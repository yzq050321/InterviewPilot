"""Batch 10A expiration regression: SQLite + fake AI, no external I/O."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.admin_auth import require_admin
from app.database import Base, get_db
from app.models import JobPosting
from app import job_routes
from main import app


@pytest.fixture
def sandbox(monkeypatch):
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)

    def database():
        with maker() as db:
            yield db

    app.dependency_overrides[get_db] = database
    monkeypatch.setattr(job_routes, "generate_question_agent", lambda *a, **kw: "请介绍你的项目。")
    try:
        with TestClient(app) as http:
            yield http, maker
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def create_job(http, days=7):
    return http.post('/api/admin/jobs', json={
        'title': '测试岗位', 'position': '后端实习', 'requirements': '熟悉 Python',
        'difficulty': '中等', 'invite_valid_days': days,
    })


def test_admin_auth_and_duration_validation(sandbox):
    http, _ = sandbox
    assert create_job(http).status_code == 401
    app.dependency_overrides[require_admin] = lambda: None
    assert create_job(http, 0).status_code == 422
    assert create_job(http, 365).status_code == 422
    response = create_job(http, 14)
    assert response.status_code == 201, response.text
    assert response.json()['invite_expires_at'] is not None
    stamp = datetime.fromisoformat(response.json()['invite_expires_at'])
    assert (job_routes._utc_now() + timedelta(days=13)) < stamp < (job_routes._utc_now() + timedelta(days=15))


def test_expiration_blocks_public_read_and_create_before_ai(sandbox, monkeypatch):
    http, maker = sandbox
    app.dependency_overrides[require_admin] = lambda: None
    created = create_job(http).json()
    code = created['invite_code']
    assert http.get(f'/api/job-invitations/{code}').status_code == 200
    with maker() as db:
        job = db.get(JobPosting, created['job_id'])
        job.invite_expires_at = job_routes._utc_now() - timedelta(seconds=1)
        db.commit()

    def should_not_call(*args, **kwargs):
        raise AssertionError('AI must not be called for expired invitations')
    monkeypatch.setattr(job_routes, 'generate_question_agent', should_not_call)
    assert http.get(f'/api/job-invitations/{code}').status_code == 410
    assert http.post(f'/api/job-invitations/{code}/interviews', json={'candidate_name': '测试'}).status_code == 410
    assert http.get('/api/admin/jobs').json()[0]['invite_expires_at'] is not None


def test_deactivate_still_rejects_and_active_link_creates(sandbox):
    http, _ = sandbox
    app.dependency_overrides[require_admin] = lambda: None
    created = create_job(http).json()
    code = created['invite_code']
    invitation = http.post(f'/api/job-invitations/{code}/interviews', json={'candidate_name': '测试甲'})
    assert invitation.status_code == 201, invitation.text
    assert invitation.json()['interview_token']
    assert http.patch(f"/api/admin/jobs/{created['job_id']}/deactivate").status_code == 200
    assert http.get(f'/api/job-invitations/{code}').status_code == 404
    assert http.post(f'/api/job-invitations/{code}/interviews', json={'candidate_name': '测试乙'}).status_code == 404


def test_null_expiration_fails_closed(sandbox):
    http, maker = sandbox
    app.dependency_overrides[require_admin] = lambda: None
    created = create_job(http).json()
    with maker() as db:
        db.get(JobPosting, created['job_id']).invite_expires_at = None
        db.commit()
    assert http.get(f"/api/job-invitations/{created['invite_code']}").status_code == 410
