"""Batch 10B: SQLite ASGI tests with fake AI; no external API calls or MySQL writes."""
from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app.database import Base, get_db
from app.models import AnswerAttempt, Message
from app import interview_create_limiter as limiter
from app.answer_idempotency import utc_now


@pytest.fixture
def ctx(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)

    def get_test_db():
        with maker() as db:
            yield db

    calls = {"first": 0, "next": 0}

    def first(*_args, **_kwargs):
        calls["first"] += 1
        return "说说你的项目"

    def next_question(*_args, **_kwargs):
        calls["next"] += 1
        return "能举个更具体的例子吗？"

    monkeypatch.setattr(main, "generate_question_agent", first)
    monkeypatch.setattr(main, "generate_followup_agent", next_question)
    main.app.dependency_overrides[get_db] = get_test_db
    with limiter._LOCK:
        limiter._EVENTS.clear()
    try:
        with TestClient(main.app) as client:
            r = client.post("/api/interviews", json={"candidate_name": "测试甲", "position": "后端工程师"})
            assert r.status_code == 200, r.text
            created = r.json()
            assert isinstance(created["question_id"], int)
            yield client, maker, calls, created
    finally:
        main.app.dependency_overrides.clear()
        with limiter._LOCK:
            limiter._EVENTS.clear()
        engine.dispose()


def send(client, created, request_id, question_id=None, answer="我会先写测试"):
    return client.post("/api/interviews/followup", headers={
        "Authorization": f"Bearer {created['interview_token']}"
    }, json={
        "interview_id": created["interview_id"],
        "question_id": question_id or created["question_id"],
        "request_id": str(request_id),
        "answer": answer,
    })


def test_same_request_replays_without_new_ai_or_messages(ctx):
    client, maker, calls, created = ctx
    rid = uuid4()
    one = send(client, created, rid)
    assert one.status_code == 200, one.text
    assert one.json()["replayed"] is False
    assert isinstance(one.json()["question_id"], int)
    again = send(client, created, rid)
    assert again.status_code == 200, again.text
    assert again.json()["replayed"] is True
    assert again.json()["next_question"] == one.json()["next_question"]
    assert again.json()["question_id"] == one.json()["question_id"]
    assert calls["next"] == 1
    with maker() as db:
        items = db.scalars(select(Message).where(Message.interview_id == created["interview_id"])).all()
    assert len(items) == 3  # original question, one answer, one follow-up


def test_second_request_for_old_question_cannot_advance(ctx):
    client, _maker, calls, created = ctx
    assert send(client, created, uuid4()).status_code == 200
    rejected = send(client, created, uuid4())
    assert rejected.status_code == 409
    assert calls["next"] == 1


def test_different_answer_cannot_reuse_identifier(ctx):
    client, _maker, calls, created = ctx
    rid = uuid4()
    assert send(client, created, rid).status_code == 200
    assert send(client, created, rid, answer="另一种答案").status_code == 409
    assert calls["next"] == 1


def test_processing_request_returns_conflict_without_ai(ctx):
    client, maker, calls, created = ctx
    import hashlib
    rid = uuid4()
    with maker() as db:
        db.add(AnswerAttempt(
            interview_id=created["interview_id"],
            question_id=created["question_id"],
            request_id=str(rid),
            answer_hash=hashlib.sha256("我会先写测试".encode()).hexdigest(),
            status="processing",
            started_at=utc_now(),
        ))
        db.commit()
    assert send(client, created, rid).status_code == 409
    assert send(client, created, uuid4()).status_code == 409
    assert calls["next"] == 0


def test_failed_request_can_retry_same_identifier(ctx):
    client, maker, calls, created = ctx
    import hashlib
    rid = uuid4()
    with maker() as db:
        db.add(AnswerAttempt(
            interview_id=created["interview_id"],
            question_id=created["question_id"],
            request_id=str(rid),
            answer_hash=hashlib.sha256("我会先写测试".encode()).hexdigest(),
            status="failed",
            started_at=utc_now() - timedelta(minutes=1),
        ))
        db.commit()
    resp = send(client, created, rid)
    assert resp.status_code == 200, resp.text
    assert calls["next"] == 1


def test_wrong_candidate_token_cannot_replay(ctx):
    client, _maker, calls, created = ctx
    rid = uuid4()
    assert send(client, created, rid).status_code == 200
    response = client.post("/api/interviews/followup", headers={
        "Authorization": "Bearer invalid-token"
    }, json={
        "interview_id": created["interview_id"],
        "question_id": created["question_id"],
        "request_id": str(rid),
        "answer": "我会先写测试",
    })
    assert response.status_code == 401
    assert calls["next"] == 1


def test_complete_blocked_while_turn_processing(ctx):
    client, maker, calls, created = ctx
    import hashlib
    with maker() as db:
        db.add(AnswerAttempt(
            interview_id=created["interview_id"], question_id=created["question_id"],
            request_id=str(uuid4()),
            answer_hash=hashlib.sha256("等待中".encode()).hexdigest(),
            status="processing", started_at=utc_now(),
        ))
        db.commit()
    r = client.patch(f"/api/interviews/{created['interview_id']}/complete", headers={
        "Authorization": f"Bearer {created['interview_token']}"
    })
    assert r.status_code == 409
