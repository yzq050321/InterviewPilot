"""Local ASGI/SQLite integration tests: fake LLM, no MySQL writes/API costs."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app.database import Base, get_db
from app.models import Interview, JobPosting
from app.admin_auth import require_admin
from app import job_routes
from app import interview_create_limiter as limiter


@pytest.fixture
def env(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    LocalSession = sessionmaker(bind=engine)

    def override_db():
        with LocalSession() as db:
            yield db

    main.app.dependency_overrides[get_db] = override_db
    main.app.dependency_overrides[require_admin] = lambda: None
    monkeypatch.setattr(main, "SessionLocal", LocalSession)
    seen = {"questions": [], "followups": [], "evaluations": []}

    def fake_question(position, difficulty, requirements=None):
        seen["questions"].append((position, difficulty, requirements))
        return "请描述如何设计 Python 接口。"

    def fake_followup(position, difficulty, history, requirements=None):
        seen["followups"].append((position, difficulty, requirements, history))
        return "请补充具体的接口设计步骤。"

    def fake_evaluation(**kwargs):
        seen["evaluations"].append(kwargs)
        return SimpleNamespace(
            technical_score=70, completeness_score=65,
            clarity_score=80, overall_score=72,
            summary="仅供 HR 辅助参考", strengths=["表达完整"],
            weaknesses=["缺少例子"], suggestions=["补充实践案例"],
        )

    monkeypatch.setattr(job_routes, "generate_question_agent", fake_question)
    monkeypatch.setattr(main, "generate_question_agent", fake_question)
    monkeypatch.setattr(main, "generate_followup_agent", fake_followup)
    monkeypatch.setattr(main, "generate_evaluation", fake_evaluation)

    with limiter._LOCK:
        limiter._EVENTS.clear()
    try:
        with TestClient(main.app) as client:
            yield client, LocalSession, seen
    finally:
        main.app.dependency_overrides.clear()
        with limiter._LOCK:
            limiter._EVENTS.clear()
        engine.dispose()


def _create_job(client):
    response = client.post("/api/admin/jobs", json={
        "title": "V2 测试任务", "position": "Python 开发",
        "requirements": "熟悉 FastAPI 和 MySQL", "difficulty": "中等",
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_invited_interview_passes_requirements_and_keeps_privacy(env):
    client, LocalSession, seen = env
    job = _create_job(client)
    code = job["invite_code"]
    response = client.post(
        f"/api/job-invitations/{code}/interviews",
        json={"candidate_name": "测试候选人"},
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert seen["questions"][-1] == ("Python 开发", "中等", "熟悉 FastAPI 和 MySQL")
    with LocalSession() as db:
        interview = db.get(Interview, created["interview_id"])
        assert interview.job_id == job["job_id"]

    iid = created["interview_id"]
    # Candidate-only interview detail requires the per-interview token.
    assert client.get(f"/api/interviews/{iid}").status_code == 401
    headers = {"Authorization": f"Bearer {created['interview_token']}"}
    assert client.get(f"/api/interviews/{iid}", headers=headers).status_code == 200
    r = client.post("/api/interviews/followup", headers=headers, json={
        "interview_id": iid, "answer": "我会 SQLAlchemy",
    })
    assert r.status_code == 200, r.text
    assert seen["followups"][-1][2] == "熟悉 FastAPI 和 MySQL"
    assert client.patch(f"/api/interviews/{iid}/complete", headers=headers).status_code == 200

    r = client.post(f"/api/interviews/{iid}/evaluation", headers=headers)
    assert r.status_code == 200, r.text
    assert seen["evaluations"][-1]["requirements"] == "熟悉 FastAPI 和 MySQL"
    # Evaluation GET has admin-only route; candidate bearer does not grant access.
    main.app.dependency_overrides.pop(require_admin)
    try:
        assert client.get(f"/api/interviews/{iid}/evaluation", headers=headers).status_code == 401
    finally:
        main.app.dependency_overrides[require_admin] = lambda: None


def test_invitation_rate_limited_before_ai_call(env):
    client, LocalSession, seen = env
    job = _create_job(client)
    endpoint = f"/api/job-invitations/{job['invite_code']}/interviews"
    for i in range(5):
        response = client.post(endpoint, json={"candidate_name": f"候选人{i}"})
        assert response.status_code == 201, response.text
    response = client.post(endpoint, json={"candidate_name": "再次创建"})
    assert response.status_code == 429
    assert len(seen["questions"]) == 5


def test_legacy_create_still_uses_old_two_arg_generator(env):
    client, LocalSession, seen = env
    response = client.post("/api/interviews", json={
        "candidate_name": "旧入口测试", "position": "Python 开发", "difficulty": "中等"
    })
    assert response.status_code == 200, response.text
    assert seen["questions"][-1][2] is None
    with LocalSession() as db:
        interview = db.get(Interview, response.json()["interview_id"])
        assert interview.job_id is None
