"""Run from backend/: python -m pytest -q tests/test_job_routes_v2.py

The tests use in-memory SQLite and a fake LLM. They do not touch MySQL or
send real DeepSeek requests.
"""
import importlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.admin_auth import require_admin
from app.candidate_auth import verify_candidate_token
from app.database import Base, get_db
from app.models import Interview
from main import app

routes = importlib.import_module("app.job_routes")


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(
        routes, "generate_question_agent", lambda position, difficulty: "请介绍一个相关项目。"
    )
    try:
        with TestClient(app) as test_client:
            yield test_client, factory
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_admin_protected_and_job_invite_flow(client):
    http, factory = client
    payload = {
        "title": "Python 后端实习生",
        "position": "Python 后端开发",
        "requirements": "熟悉 Python、FastAPI、MySQL",
        "difficulty": "中等",
    }

    # No JWT => cannot create/list/deactivate HR jobs.
    assert http.post("/api/admin/jobs", json=payload).status_code == 401
    assert http.get("/api/admin/jobs").status_code == 401
    assert http.patch("/api/admin/jobs/1/deactivate").status_code == 401

    app.dependency_overrides[require_admin] = lambda: None

    created = http.post("/api/admin/jobs", json=payload)
    assert created.status_code == 201, created.text
    job = created.json()
    assert job["job_id"] > 0
    assert job["is_active"] is True
    assert job["invite_path"].startswith("/invite/")
    code = job["invite_code"]
    assert len(code) >= 24
    assert code not in payload.values()

    jobs = http.get("/api/admin/jobs")
    assert jobs.status_code == 200
    assert jobs.json()[0]["job_id"] == job["job_id"]

    public = http.get(f"/api/job-invitations/{code}")
    assert public.status_code == 200
    assert set(public.json()) == {"title", "position", "requirements", "difficulty"}
    assert "invite_code" not in public.json()
    assert "candidate_token" not in public.json()

    # Guests cannot override HR-chosen position or difficulty.
    invalid_extra = http.post(
        f"/api/job-invitations/{code}/interviews",
        json={"candidate_name": "测试候选人", "position": "不应被采用", "difficulty": "困难"},
    )
    assert invalid_extra.status_code == 422
    interview_response = http.post(
        f"/api/job-invitations/{code}/interviews",
        json={"candidate_name": "测试候选人"},
    )
    assert interview_response.status_code == 201, interview_response.text
    result = interview_response.json()
    assert result["position"] == payload["position"]
    assert result["difficulty"] == "中等"
    assert result["question"] == "请介绍一个相关项目。"
    assert result["interview_token"]

    with factory() as db:
        interview = db.scalar(select(Interview).where(Interview.id == result["interview_id"]))
        assert interview is not None
        assert interview.job_id == job["job_id"]
        assert interview.candidate_token_hash != result["interview_token"]
        assert verify_candidate_token(result["interview_token"], interview.candidate_token_hash)
        assert len(interview.messages) == 1

    disabled = http.patch(f"/api/admin/jobs/{job['job_id']}/deactivate")
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert http.get(f"/api/job-invitations/{code}").status_code == 404
    assert http.post(
        f"/api/job-invitations/{code}/interviews",
        json={"candidate_name": "候选人乙"},
    ).status_code == 404


def test_invalid_invitation_and_invalid_job_data(client):
    http, _ = client
    assert http.get("/api/job-invitations/not-a-real-code").status_code == 404
    assert http.post(
        "/api/job-invitations/not-a-real-code/interviews",
        json={"candidate_name": "张三"},
    ).status_code == 404

    app.dependency_overrides[require_admin] = lambda: None
    assert http.post(
        "/api/admin/jobs",
        json={"title": "   ", "position": "Python", "requirements": "技术岗位"},
    ).status_code == 422
