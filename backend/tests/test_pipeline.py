"""Batch 9 HTTP security and transaction tests (SQLite; never needs MySQL)."""
from __future__ import annotations
import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.admin_auth import create_admin_token, create_demo_token
from app.database import Base, get_db
from app.demo_routes import router as demo_router, DEMO_INTERVIEW_ID
from app.models import Interview, InterviewFollowup
from app.pipeline import router as pipeline_router

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("ADMIN_JWT_SECRET", "x" * 64)
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("DEMO_USERNAME", "demo")
    monkeypatch.setenv("DEMO_PASSWORD_HASH", "configured-demo-hash")
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Interview(candidate_name="测试候选人", position="Python 实习生",
                              difficulty="中等", status="completed"))
        session.commit()
    app = FastAPI()
    app.include_router(pipeline_router)
    app.include_router(demo_router)
    def override_db():
        with Session(engine) as session: yield session
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as http:
        yield http, engine, {"Authorization": f"Bearer {create_admin_token()}"},             {"Authorization": f"Bearer {create_demo_token()}"}
    engine.dispose()


def test_admin_can_update_and_log_history(client):
    http, engine, admin, _ = client
    url = "/api/admin/interviews/1/pipeline"
    assert http.get(url, headers=admin).json()["stage"] == "new"
    for stage, note in [("contact", "计划电话确认岗位意向"), ("next_round", "沟通结束，安排下一轮")]:
        r = http.post(url, headers=admin, json={"stage": stage, "note": note})
        assert r.status_code == 200, r.text
    detail = http.get(url, headers=admin).json()
    assert detail["stage"] == "next_round"
    assert len(detail["history"]) == 2
    assert detail["history"][0]["old_stage"] == "contact"
    with Session(engine) as session:
        assert session.scalar(select(Interview).where(Interview.id == 1)).review_status == "pending"
        assert len(session.scalars(select(InterviewFollowup)).all()) == 2


def test_reject_invalid_payload_without_mutation(client):
    http, _, admin, _ = client
    url = "/api/admin/interviews/1/pipeline"
    for payload in [{"stage": "hired", "note": "不支持"},
                    {"stage": "contact", "note": "  "},
                    {"stage": "contact", "note": "ok", "review_status": "reviewed"}]:
        assert http.post(url, headers=admin, json=payload).status_code == 422
    assert http.get(url, headers=admin).json()["history"] == []
    assert http.post("/api/admin/interviews/999/pipeline", headers=admin,
                     json={"stage": "contact", "note": "测试"}).status_code == 404


def test_demo_cannot_access_real_pipeline(client):
    http, _, admin, demo = client
    assert http.get("/api/admin/pipeline", headers=demo).status_code == 401
    assert http.get("/api/admin/interviews/1/pipeline", headers=demo).status_code == 401
    assert http.post("/api/admin/interviews/1/pipeline", headers=demo,
                     json={"stage": "closed", "note": "测试"}).status_code == 401
    assert http.get("/api/admin/pipeline").status_code == 401
    assert http.get("/api/demo/pipeline", headers=admin).status_code == 401
    assert http.get("/api/demo/pipeline", headers=demo).json()[0]["interview_id"] == DEMO_INTERVIEW_ID
    assert http.get(f"/api/demo/interviews/{DEMO_INTERVIEW_ID}/pipeline", headers=demo).status_code == 200
    assert http.post(f"/api/demo/interviews/{DEMO_INTERVIEW_ID}/pipeline", headers=demo,
                     json={"stage": "closed", "note": "测试"}).status_code == 405


def test_note_only_update_and_overview(client):
    http, _, admin, _ = client
    r = http.post("/api/admin/interviews/1/pipeline", headers=admin,
                  json={"stage": "new", "note": "等待候选人确认时间"})
    assert r.status_code == 200
    assert r.json()["followup"]["old_stage"] == "new"
    assert http.get("/api/admin/pipeline", headers=admin).json() == [{"interview_id": 1, "stage": "new"}]
