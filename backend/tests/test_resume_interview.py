"""V2.2 resume interview API tests with fake AI and SQLite; no external calls."""
from datetime import timedelta
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app import interview_create_limiter as limiter
from app import job_routes
from app.admin_auth import require_admin
from app.database import Base, get_db
from app.models import Interview


def make_docx(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def env(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    LocalSession = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with LocalSession() as db:
            yield db

    main.app.dependency_overrides[get_db] = override_db
    main.app.dependency_overrides[require_admin] = lambda: None
    captured = {"resume_text": None, "calls": 0}

    def fake_first(position, difficulty, requirements=None, resume_text=None):
        captured["calls"] += 1
        captured["resume_text"] = resume_text
        return "请介绍你简历里的 FastAPI 项目。"

    monkeypatch.setattr(job_routes, "generate_question_agent", fake_first)
    with limiter._LOCK:
        limiter._EVENTS.clear()
    try:
        with TestClient(main.app) as client:
            yield client, LocalSession, captured
    finally:
        main.app.dependency_overrides.clear()
        with limiter._LOCK:
            limiter._EVENTS.clear()
        engine.dispose()


def create_job(client: TestClient) -> dict:
    response = client.post("/api/admin/jobs", json={
        "title": "V2.2 简历面试",
        "position": "Python 后端实习生",
        "requirements": "熟悉 Python、FastAPI、MySQL",
        "difficulty": "中等",
    })
    assert response.status_code == 201, response.text
    return response.json()


def upload_resume(client: TestClient, code: str, *, consent: str = "true", filename: str = "resume.docx"):
    return client.post(
        f"/api/job-invitations/{code}/interviews/with-resume",
        data={"candidate_name": "测试候选人", "consent": consent},
        files={"resume": (
            filename,
            make_docx(
                "张三，Python 后端实习生。项目使用 FastAPI、MySQL、SQLAlchemy，"
                "负责接口设计、数据库建模和自动化测试。"
            ),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )},
    )


def test_resume_interview_stores_text_and_passes_it_to_ai(env):
    client, LocalSession, captured = env
    job = create_job(client)
    response = upload_resume(client, job["invite_code"])
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["has_resume"] is True
    assert body["resume_filename"] == "resume.docx"
    assert "FastAPI" in body["question"]

    with LocalSession() as db:
        interview = db.get(Interview, body["interview_id"])
        assert interview is not None
        assert "FastAPI" in interview.resume_text
        assert interview.resume_filename == "resume.docx"
        assert interview.resume_consent_at is not None
    assert "FastAPI" in captured["resume_text"]


def test_resume_requires_consent(env):
    client, LocalSession, captured = env
    job = create_job(client)
    response = upload_resume(client, job["invite_code"], consent="false")
    assert response.status_code == 422
    assert captured["calls"] == 0
    with LocalSession() as db:
        assert db.scalar(select(Interview.id)) is None


def test_resume_rejects_unsupported_file(env):
    client, _LocalSession, captured = env
    job = create_job(client)
    response = upload_resume(client, job["invite_code"], filename="resume.txt")
    assert response.status_code == 400
    assert captured["calls"] == 0


def test_resume_is_rejected_after_invitation_expires(env):
    client, LocalSession, captured = env
    job = create_job(client)
    with LocalSession() as db:
        posting = db.get(job_routes.JobPosting, job["job_id"])
        posting.invite_expires_at = job_routes._utc_now() - timedelta(seconds=1)
        db.commit()

    response = upload_resume(client, job["invite_code"])
    assert response.status_code == 410
    assert captured["calls"] == 0


def test_followup_receives_resume_text(env, monkeypatch):
    client, _LocalSession, _captured = env
    job = create_job(client)
    created = upload_resume(client, job["invite_code"]).json()
    seen = {}

    def fake_followup(position, difficulty, history, requirements=None, resume_text=None):
        seen["resume_text"] = resume_text
        return "请具体说说这个接口的数据库设计。"

    monkeypatch.setattr(main, "generate_followup_agent", fake_followup)
    response = client.post(
        "/api/interviews/followup",
        headers={"Authorization": f"Bearer {created['interview_token']}"},
        json={
            "interview_id": created["interview_id"],
            "question_id": created["question_id"],
            "request_id": str(uuid4()),
            "answer": "我负责了岗位和面试记录接口。",
        },
    )
    assert response.status_code == 200, response.text
    assert "FastAPI" in seen["resume_text"]


def test_evaluation_receives_resume_as_reference(monkeypatch):
    from app.services import evaluation_service

    messages = []

    def fake_invoke(payload):
        messages.append(payload)
        return SimpleNamespace(content='''{
          "technical_score": 60, "completeness_score": 60,
          "clarity_score": 60, "overall_score": 60,
          "summary": "仅供人工复核", "strengths": [], "weaknesses": [], "suggestions": []
        }''')

    monkeypatch.setattr(evaluation_service, "llm", SimpleNamespace(invoke=fake_invoke))
    history = [
        {"role": "assistant", "content": "请介绍项目"},
        {"role": "user", "content": "我用了 FastAPI。"},
    ]
    evaluation_service.generate_evaluation(
        "Python 后端", "中等", history,
        requirements="FastAPI", resume_text="候选人简历：FastAPI 项目经验",
    )
    assert "候选人简历" in messages[-1][-1].content
