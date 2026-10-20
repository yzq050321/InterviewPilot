"""Run from backend/: python -m pytest -q tests/test_demo_account.py

Only synthetic fixtures. No real MySQL connections or DeepSeek calls.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

import main
from app.admin_auth import hash_password, verify_admin_token, verify_demo_token
from app.login_limiter import clear_login_failures


@pytest.fixture
def http(monkeypatch):
    # Source credentials never appear in the ZIP; passwords are only dummy test fixtures.
    monkeypatch.setenv("ADMIN_USERNAME", "local_test_owner")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", hash_password("local-only-owner-password-2026"))
    monkeypatch.setenv("DEMO_USERNAME", "local_test_demo")
    monkeypatch.setenv("DEMO_PASSWORD_HASH", hash_password("local-only-demo-password-2026"))
    monkeypatch.setenv("ADMIN_JWT_SECRET", "local-only-unit-test-secret-not-for-any-server-2026")
    clear_login_failures("testclient")
    with TestClient(main.app) as client:
        yield client
    clear_login_failures("testclient")


def login(client, username, password):
    return client.post("/api/admin/login", json={"username": username, "password": password})


def auth(token):
    return {"Authorization": "Bearer " + token}


def test_login_role_separation_and_backward_compatibility(http):
    admin = login(http, "local_test_owner", "local-only-owner-password-2026")
    demo = login(http, "local_test_demo", "local-only-demo-password-2026")
    assert admin.status_code == demo.status_code == 200
    assert admin.json()["role"] == "admin"
    assert demo.json()["role"] == "demo"
    assert verify_admin_token(admin.json()["access_token"])
    assert not verify_demo_token(admin.json()["access_token"])
    assert verify_demo_token(demo.json()["access_token"])
    assert not verify_admin_token(demo.json()["access_token"])
    assert login(http, "local_test_demo", "wrong").status_code == 401


def test_demo_cannot_access_real_hr_endpoints_or_modify_any_data(http):
    demo_token = login(http, "local_test_demo", "local-only-demo-password-2026").json()["access_token"]
    headers = auth(demo_token)
    # Every existing real HR endpoint still uses require_admin.
    assert http.get("/api/admin/jobs", headers=headers).status_code == 401
    assert http.post("/api/admin/jobs", headers=headers, json={
        "title":"fake", "position":"fake", "requirements":"fake", "difficulty":"中等"
    }).status_code == 401
    assert http.patch("/api/admin/jobs/1/deactivate", headers=headers).status_code == 401
    assert http.get("/api/interviews", headers=headers).status_code == 401
    assert http.get("/api/admin/interviews/1", headers=headers).status_code == 401
    assert http.get("/api/interviews/1/evaluation", headers=headers).status_code == 401
    assert http.post("/api/admin/interviews/1/evaluation/retry", headers=headers).status_code == 401
    assert http.patch("/api/admin/interviews/1/review", headers=headers, json={
        "review_status":"reviewed", "review_note":"must fail"
    }).status_code == 401
    assert http.post("/api/demo/jobs", headers=headers).status_code == 405
    # 该 URL 没有任何路由：FastAPI 正确返回 404；若 URL 存在但方法不支持，才是 405。
    assert http.patch("/api/demo/interviews/900000001/review", headers=headers).status_code == 404


def test_demo_reads_only_static_synthetic_records(http):
    token = login(http, "local_test_demo", "local-only-demo-password-2026").json()["access_token"]
    headers = auth(token)
    jobs = http.get("/api/demo/jobs", headers=headers)
    interviews = http.get("/api/demo/interviews", headers=headers)
    assert jobs.status_code == 200 and interviews.status_code == 200
    assert len(jobs.json()) == 1 and len(interviews.json()) == 2
    assert "虚构" in jobs.json()[0]["title"]
    interview_id = interviews.json()[0]["interview_id"]
    detail = http.get(f"/api/demo/interviews/{interview_id}", headers=headers)
    report = http.get(f"/api/demo/interviews/{interview_id}/evaluation", headers=headers)
    assert detail.status_code == report.status_code == 200
    assert len(detail.json()["messages"]) == 16
    assert set(report.json()["competency_assessment"]["dimensions"]) == {
        "technical", "communication", "learning", "execution"
    }
    assert http.get("/api/demo/interviews/1", headers=headers).status_code == 404
    assert http.get("/api/demo/interviews/1/evaluation", headers=headers).status_code == 404
    assert http.get("/api/demo/interviews/900000002/evaluation", headers=headers).status_code == 404
    assert "token" not in str(jobs.json()).lower()


def test_demo_fixtures_require_demo_role_and_valid_signature(http):
    assert http.get("/api/demo/jobs").status_code == 401
    admin_token = login(http, "local_test_owner", "local-only-owner-password-2026").json()["access_token"]
    assert http.get("/api/demo/jobs", headers=auth(admin_token)).status_code == 401
    forged = jwt.encode({"role":"demo", "sub":"demo", "iat":datetime.now(timezone.utc),
                         "exp":datetime.now(timezone.utc)+timedelta(hours=2)},
                        "attacker-secret-does-not-work", algorithm="HS256")
    assert http.get("/api/demo/jobs", headers=auth(forged)).status_code == 401
    expired = jwt.encode({"role":"demo", "sub":"demo",
                          "iat":datetime.now(timezone.utc)-timedelta(hours=5),
                          "exp":datetime.now(timezone.utc)-timedelta(hours=3)},
                         "local-only-unit-test-secret-not-for-any-server-2026", algorithm="HS256")
    assert http.get("/api/demo/jobs", headers=auth(expired)).status_code == 401


def test_unsetting_demo_config_disables_login_and_issued_tokens(http, monkeypatch):
    token = login(http, "local_test_demo", "local-only-demo-password-2026").json()["access_token"]
    monkeypatch.delenv("DEMO_PASSWORD_HASH")
    assert login(http, "local_test_demo", "local-only-demo-password-2026").status_code == 401
    assert http.get("/api/demo/jobs", headers=auth(token)).status_code == 401


def test_demo_username_must_differ_from_admin_username(http, monkeypatch):
    monkeypatch.setenv("DEMO_USERNAME", "local_test_owner")
    assert login(http, "local_test_owner", "local-only-demo-password-2026").status_code == 401
