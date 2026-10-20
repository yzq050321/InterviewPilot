"""Batch 6 API tests; all AI calls are faked, never touch MySQL / DeepSeek."""
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app import admin_workflow
from app.admin_auth import require_admin
from app.candidate_auth import create_candidate_token
from app.database import Base, get_db
from app.evaluation_workflow import get_evaluation_state, utc_naive
from app.models import Evaluation, Interview, Message


@pytest.fixture
def sandbox(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    token, hashed = create_candidate_token()
    with maker() as db:
        a = Interview(id=1, candidate_name="测试候选人", candidate_token_hash=hashed,
                      position="Python 后端", difficulty="中等", status="completed")
        b = Interview(id=2, candidate_name="进行中候选人", position="Python 后端",
                      difficulty="中等", status="in_progress")
        db.add_all([a, b])
        db.add_all([Message(interview_id=1, role="assistant", content="如何管理依赖？"),
                    Message(interview_id=1, role="user", content="可以使用依赖注入。")])
        db.commit()

    def get_test_db():
        with maker() as db:
            yield db

    main.app.dependency_overrides[get_db] = get_test_db
    monkeypatch.setattr(main, "SessionLocal", maker)
    monkeypatch.setattr(admin_workflow, "SessionLocal", maker)
    calls = []

    def fake_model(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(technical_score=75, completeness_score=75,
                               clarity_score=75, overall_score=75,
                               summary="测试评估", strengths=["测试"], weaknesses=["待复核"],
                               suggestions=["请人工确认"], competency_assessment=None)

    monkeypatch.setattr(main, "generate_evaluation", fake_model)
    monkeypatch.setattr(admin_workflow, "generate_evaluation", fake_model)
    client = TestClient(main.app)
    yield client, maker, token, calls
    main.app.dependency_overrides.clear()
    engine.dispose()


def authorize_admin():
    main.app.dependency_overrides[require_admin] = lambda: None


def test_hr_recovery_requires_admin(sandbox):
    client, _, _, calls = sandbox
    r = client.post("/api/admin/interviews/1/evaluation/retry")
    assert r.status_code == 401
    assert not calls


def test_candidate_cannot_see_hr_report(sandbox):
    client, maker, token, calls = sandbox
    assert client.post("/api/interviews/1/evaluation").status_code == 401
    r = client.post("/api/interviews/1/evaluation", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert "overall_score" not in r.json() and "competency_assessment" not in r.json()
    with maker() as db:
        assert db.scalar(select(Evaluation.id).where(Evaluation.interview_id == 1)) is not None
        assert db.get(Interview, 1).evaluation_state == "ready"
    assert len(calls) == 1


def test_admin_retries_missing_report(sandbox):
    client, maker, _, calls = sandbox
    authorize_admin()
    r = client.post("/api/admin/interviews/1/evaluation/retry")
    assert r.status_code == 200, r.text
    assert len(calls) == 1
    duplicate = client.post("/api/admin/interviews/1/evaluation/retry")
    assert duplicate.status_code == 409
    assert len(calls) == 1
    summary = client.get("/api/interviews")
    assert summary.status_code == 200, summary.text
    statuses = {v["interview_id"]: v["evaluation_status"] for v in summary.json()}
    assert statuses == {1: "ready", 2: "not_started"}


def test_failure_saved_and_recoverable(sandbox, monkeypatch):
    client, maker, _, calls = sandbox
    authorize_admin()

    def broken(**kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(admin_workflow, "generate_evaluation", broken)
    assert client.post("/api/admin/interviews/1/evaluation/retry").status_code == 502
    with maker() as db:
        assert db.get(Interview, 1).evaluation_state == "failed"
        assert db.scalar(select(Evaluation.id)) is None
    monkeypatch.setattr(admin_workflow, "generate_evaluation", lambda **kwargs: SimpleNamespace(
        technical_score=None, completeness_score=None, clarity_score=None, overall_score=None,
        summary="缺少证据", strengths=[], weaknesses=[], suggestions=[], competency_assessment=None))
    assert client.post("/api/admin/interviews/1/evaluation/retry").status_code == 200


def test_concurrent_slot_is_not_reused(sandbox):
    client, maker, _, calls = sandbox
    authorize_admin()
    with maker() as db:
        item = db.get(Interview, 1)
        item.evaluation_state = "generating"
        item.evaluation_started_at = utc_naive()
        db.commit()
    assert client.post("/api/admin/interviews/1/evaluation/retry").status_code == 409
    assert not calls


def test_stale_generation_can_retry(sandbox):
    client, maker, _, calls = sandbox
    authorize_admin()
    with maker() as db:
        item = db.get(Interview, 1)
        item.evaluation_state = "generating"
        item.evaluation_started_at = utc_naive() - timedelta(minutes=17)
        db.commit()
    assert client.post("/api/admin/interviews/1/evaluation/retry").status_code == 200
    assert len(calls) == 1


def test_review_rejects_missing_report_or_incomplete(sandbox):
    client, _, _, _ = sandbox
    authorize_admin()
    payload = {"review_status": "reviewed", "review_note": "需要核实"}
    assert client.patch("/api/admin/interviews/1/review", json=payload).status_code == 409
    assert client.patch("/api/admin/interviews/2/review", json=payload).status_code == 409
    assert client.patch("/api/admin/interviews/999/review", json=payload).status_code == 404
    assert client.patch("/api/admin/interviews/1/review", json={"review_status": "hire"}).status_code == 422


def test_review_is_hr_only_and_persists(sandbox):
    client, maker, _, _ = sandbox
    authorize_admin()
    assert client.post("/api/admin/interviews/1/evaluation/retry").status_code == 200
    main.app.dependency_overrides.pop(require_admin)
    assert client.patch("/api/admin/interviews/1/review", json={"review_status": "reviewed", "review_note": "测试"}).status_code == 401
    authorize_admin()
    response = client.patch("/api/admin/interviews/1/review", json={
        "review_status": "follow_up", "review_note": "  需要进一步沟通  "})
    assert response.status_code == 200, response.text
    assert response.json()["review_status"] == "follow_up"
    with maker() as db:
        assert db.get(Interview, 1).review_note == "需要进一步沟通"
    detail = client.get("/api/admin/interviews/1")
    assert detail.status_code == 200
    assert detail.json()["review_status"] == "follow_up"
    assert detail.json()["review_note"] == "需要进一步沟通"


def test_legacy_report_is_ready_even_with_null_flag(sandbox):
    _, maker, _, _ = sandbox
    with maker() as db:
        item = db.get(Interview, 1)
        assert get_evaluation_state(item, True) == "ready"
        assert get_evaluation_state(item, False) == "pending"
