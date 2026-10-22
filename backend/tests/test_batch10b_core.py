"""Dependency-light SQLite tests for durable answer reservation; no DB secrets/AI."""
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Interview, Message, AnswerAttempt
from app.answer_idempotency import reserve_attempt, fail_attempt, response_from_attempt


@pytest.fixture
def turn(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    with maker() as db:
        interview = Interview(position="后端实习", candidate_name="测试甲", difficulty="中等", status="in_progress")
        db.add(interview)
        db.flush()
        question = Message(interview_id=interview.id, role="assistant", content="请谈谈你的项目")
        db.add(question)
        db.commit()
        yield db, interview, question
    engine.dispose()


def test_unique_question_and_cached_success(turn):
    db, interview, question = turn
    rid = uuid4()
    attempt = reserve_attempt(db, interview, question, rid, question.id, "先写接口")
    attempt.status = "done"
    attempt.next_question = "说说测试"
    attempt.next_question_id = question.id + 1
    attempt.next_stage = "technical_followup"
    db.commit()
    resp = reserve_attempt(db, interview, question, rid, question.id, "先写接口")
    assert isinstance(resp, dict)
    assert resp["next_question"] == "说说测试"
    assert resp["replayed"] is True
    with pytest.raises(HTTPException) as err:
        reserve_attempt(db, interview, question, uuid4(), question.id, "另一个答案")
    assert err.value.status_code == 409
    assert db.scalar(select(AnswerAttempt).where(AnswerAttempt.request_id == str(rid))) is not None


def test_processing_conflicts_and_failed_can_retry(turn):
    db, interview, question = turn
    rid = uuid4()
    attempt = reserve_attempt(db, interview, question, rid, question.id, "我会拆分步骤")
    with pytest.raises(HTTPException) as busy:
        reserve_attempt(db, interview, question, rid, question.id, "我会拆分步骤")
    assert busy.value.status_code == 409
    fail_attempt(db, attempt)
    retried = reserve_attempt(db, interview, question, rid, question.id, "我会拆分步骤")
    assert retried.id == attempt.id
    assert retried.status == "processing"
