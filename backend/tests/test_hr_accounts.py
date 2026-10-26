"""V2.3 invite-only HR registration, login, trial request, and role tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app.admin_auth import require_admin, verify_admin_token
from app.database import Base, get_db
from app.models import HRUser, TrialRequest


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("ADMIN_JWT_SECRET", "v23-test-secret-0123456789abcdef")
    monkeypatch.setenv("HR_SIGNUP_INVITE_CODE", "INVITE-ONLY-2026")
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        with maker() as db:
            yield db

    main.app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(main, "SessionLocal", maker)
    try:
        with TestClient(main.app) as client:
            yield client, maker
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


def register(client, email="hr@example.com", password="strong-pass-2026", code="INVITE-ONLY-2026"):
    return client.post("/api/auth/register", json={
        "email": email, "password": password, "invite_code": code,
    })


def test_registration_requires_invite_and_creates_hr(env):
    client, maker = env
    assert register(client, code="wrong").status_code == 403

    response = register(client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "hr"
    assert body["email"] == "hr@example.com"
    assert verify_admin_token(body["access_token"])

    with maker() as db:
        user = db.scalar(select(HRUser).where(HRUser.email == "hr@example.com"))
        assert user is not None
        assert user.password_hash != "strong-pass-2026"
        assert user.status == "active"

    assert register(client).status_code == 409


def test_registration_validation(env):
    client, _ = env
    assert register(client, password="short").status_code == 422
    assert register(client, email="not-an-email").status_code == 422


def test_registered_hr_can_login_and_access_admin_api(env):
    client, _ = env
    register(client)
    response = client.post("/api/admin/login", json={
        "username": "hr@example.com", "password": "strong-pass-2026",
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role"] == "hr"
    token = body["access_token"]

    # The HR token is accepted by the same require_admin dependency.
    assert client.get("/api/admin/jobs", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    wrong = client.post("/api/admin/login", json={
        "username": "hr@example.com", "password": "wrong-password",
    })
    assert wrong.status_code == 401


def test_disabled_hr_cannot_login(env):
    client, maker = env
    register(client)
    with maker() as db:
        user = db.scalar(select(HRUser).where(HRUser.email == "hr@example.com"))
        user.status = "disabled"
        db.commit()
    response = client.post("/api/admin/login", json={
        "username": "hr@example.com", "password": "strong-pass-2026",
    })
    assert response.status_code == 401


def test_trial_request_is_stored_and_admin_can_list(env):
    client, maker = env
    response = client.post("/api/auth/trial-request", json={
        "name": "王 HR", "email": "trial@example.com",
        "company": "测试公司", "note": "想测试简历面试",
    })
    assert response.status_code == 202, response.text
    with maker() as db:
        item = db.scalar(select(TrialRequest).where(TrialRequest.email == "trial@example.com"))
        assert item is not None and item.status == "pending"

    # Admin-only list; override auth to avoid coupling this test to env login.
    main.app.dependency_overrides[require_admin] = lambda: None
    try:
        listed = client.get("/api/admin/trial-requests")
        assert listed.status_code == 200
        assert listed.json()[0]["email"] == "trial@example.com"
    finally:
        main.app.dependency_overrides.pop(require_admin, None)
