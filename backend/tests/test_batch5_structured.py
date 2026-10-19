"""V2: scheduled dimensions, evidence verification, live route with fake LLM.

Run: cd backend && python -m pytest -q tests/test_batch5_structured.py
"""
from types import SimpleNamespace

import pytest

from app.structured_interview import (
    CLOSING_MESSAGE,
    DIMENSIONS,
    QUESTION_LIMIT,
    answers_by_dimension,
    stage_after_answer,
    verify_competency_evidence,
)


def make_history(n=8):
    history = []
    for i in range(n):
        history.extend([
            {"role": "assistant", "content": f"问题 {i}"},
            {"role": "user", "content": f"我会先分析任务情况再做对应的第{i}项处理"},
        ])
    return history


def test_stage_sequence_is_deterministic():
    assert [stage_after_answer(i) for i in range(1, 9)] == [
        "technical_followup", "communication_intro", "communication_followup",
        "learning_intro", "learning_followup", "execution_intro",
        "execution_followup", "finished",
    ]
    assert stage_after_answer(9) == "finished"
    with pytest.raises(ValueError):
        stage_after_answer(0)


def test_answers_are_grouped_by_real_answer_order():
    answer_groups = answers_by_dimension(make_history(8))
    assert [len(answer_groups[key]) for key in DIMENSIONS] == [2, 2, 2, 2]
    assert "第2项" in answer_groups["communication"][0]
    assert "第6项" in answer_groups["execution"][0]


def test_verified_quote_keeps_score():
    data = {key: {
        "score": 73,
        "evidence": f"分析任务情况再做对应的第{i*2}项处理",
        "observation": "候选人提出了行动计划",
        "limitations": "实际执行仍须人工确认",
    } for i, key in enumerate(DIMENSIONS)}
    result = verify_competency_evidence(data, make_history(8))
    assert all(result["dimensions"][key]["score"] == 73 for key in DIMENSIONS)
    assert result["version"] == 1


def test_fake_evidence_is_rejected_not_passed_to_hr():
    data = {"communication": {
        "score": 99,
        "evidence": "候选人具有卓越的沟通能力而且领导了大型跨国项目",
        "observation": "非常强",
        "limitations": "无",
    }}
    result = verify_competency_evidence(data, make_history(8))
    assert result["dimensions"]["communication"]["score"] is None
    assert result["dimensions"]["communication"]["evidence"] is None


def test_early_end_cannot_score_unasked_stages():
    data = {"execution": {"score": 98, "evidence": "第6项处理"}}
    result = verify_competency_evidence(data, make_history(2))
    assert result["dimensions"]["execution"]["score"] is None
    assert result["dimensions"]["execution"]["answer_count"] == 0


def test_score_cannot_be_boolean_or_outside_range():
    data = {"technical": {"score": True, "evidence": "分析任务情况再做对应的第0项处理"}}
    assert verify_competency_evidence(data, make_history(2))["dimensions"]["technical"]["score"] is None
    data["technical"]["score"] = 101
    assert verify_competency_evidence(data, make_history(2))["dimensions"]["technical"]["score"] is None


def test_group_does_not_accept_ninth_answer():
    result = answers_by_dimension(make_history(9))
    assert sum(map(len, result.values())) == QUESTION_LIMIT


# ASGI integration with SQLite and monkeypatched generators: no DeepSeek costs, no MySQL writes.
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app.database import Base, get_db
from app.models import Interview, Evaluation
from app.admin_auth import require_admin
from app import job_routes, interview_create_limiter as limiter


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
        with LocalSession() as session:
            yield session

    main.app.dependency_overrides[get_db] = override_db
    main.app.dependency_overrides[require_admin] = lambda: None
    monkeypatch.setattr(main, "SessionLocal", LocalSession)
    seen = {"stages": [], "followups": [], "evaluations": []}

    def fake_first(position, difficulty, requirements=None):
        return "请介绍 FastAPI 依赖注入。"

    def fake_followup(position, difficulty, history, requirements=None):
        seen["followups"].append(requirements)
        return "请补充具体技术例子。"

    def fake_competency(position, difficulty, requirements, stage, history):
        seen["stages"].append((stage, requirements))
        return f"{stage}: 请给出具体做法。"

    def fake_report(**kwargs):
        seen["evaluations"].append(kwargs)
        return SimpleNamespace(
            technical_score=70, completeness_score=68, clarity_score=75,
            overall_score=71, summary="仅供参考", strengths=["有思路"],
            weaknesses=["细节不够"], suggestions=["补充例子"],
            competency_assessment=verify_competency_evidence({}, kwargs["history"])
            if kwargs.get("structured") else None,
        )

    monkeypatch.setattr(job_routes, "generate_question_agent", fake_first)
    monkeypatch.setattr(main, "generate_question_agent", fake_first)
    monkeypatch.setattr(main, "generate_followup_agent", fake_followup)
    monkeypatch.setattr(main, "generate_competency_question_agent", fake_competency)
    monkeypatch.setattr(main, "generate_evaluation", fake_report)
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


def create_invited(client):
    job = client.post("/api/admin/jobs", json={
        "title": "V2 结构化招聘", "position": "Python 后端实习生",
        "requirements": "熟悉 Python FastAPI", "difficulty": "中等",
    })
    assert job.status_code == 201, job.text
    invited = client.post(
        f"/api/job-invitations/{job.json()['invite_code']}/interviews",
        json={"candidate_name": "虚构测试候选人"},
    )
    assert invited.status_code == 201, invited.text
    return invited.json()


def test_invited_interview_covers_four_dimensions_without_ninth_question(env):
    client, LocalSession, seen = env
    invite = create_invited(client)
    iid = invite["interview_id"]
    headers = {"Authorization": f"Bearer {invite['interview_token']}"}
    for index in range(8):
        response = client.post("/api/interviews/followup", headers=headers, json={
            "interview_id": iid, "answer": f"我的第{index + 1}个测试回答", 
        })
        assert response.status_code == 200, response.text
        if index == 7:
            assert response.json()["next_question"] == CLOSING_MESSAGE
            assert response.json()["finished_questions"] is True
    assert [stage for stage, _ in seen["stages"]] == [
        "communication_intro", "communication_followup", "learning_intro",
        "learning_followup", "execution_intro", "execution_followup",
    ]
    assert len(seen["followups"]) == 1
    again = client.post("/api/interviews/followup", headers=headers, json={
        "interview_id": iid, "answer": "不应记录第9次回答",
    })
    assert again.status_code == 409
    assert client.patch(f"/api/interviews/{iid}/complete", headers=headers).status_code == 200
    generated = client.post(f"/api/interviews/{iid}/evaluation", headers=headers)
    assert generated.status_code == 200, generated.text
    assert "overall_score" not in generated.json()
    assert "competency_assessment" not in generated.json()
    assert seen["evaluations"][-1]["structured"] is True
    report = client.get(f"/api/interviews/{iid}/evaluation")
    assert report.status_code == 200
    assert report.json()["competency_assessment"]["version"] == 1
    # 候选人不能借自己的 bearer 访问管理员报告。
    main.app.dependency_overrides.pop(require_admin)
    try:
        assert client.get(f"/api/interviews/{iid}/evaluation", headers=headers).status_code == 401
    finally:
        main.app.dependency_overrides[require_admin] = lambda: None


def test_legacy_interviews_still_follow_old_flow(env):
    client, LocalSession, seen = env
    response = client.post("/api/interviews", json={
        "candidate_name": "旧模式测试", "position": "Python 开发", "difficulty": "中等",
    })
    assert response.status_code == 200, response.text
    iid = response.json()["interview_id"]
    headers = {"Authorization": f"Bearer {response.json()['interview_token']}"}
    for n in range(2):
        followup = client.post("/api/interviews/followup", json={
            "interview_id": iid, "answer": f"旧面试回答{n}",
        }, headers=headers)
        assert followup.status_code == 200, followup.text
    assert len(seen["stages"]) == 0
    assert len(seen["followups"]) == 2
    assert client.patch(f"/api/interviews/{iid}/complete", headers=headers).status_code == 200
    generated = client.post(f"/api/interviews/{iid}/evaluation", headers=headers)
    assert generated.status_code == 200, generated.text
    assert seen["evaluations"][-1].get("structured") is None
    assert client.get(f"/api/interviews/{iid}/evaluation").json()["competency_assessment"] is None


def test_actual_evaluation_sanitizes_llm_claims(monkeypatch):
    import json
    from app.services import evaluation_service

    fake_output = {
        "technical_score": 60, "completeness_score": 60,
        "clarity_score": 60, "overall_score": 60,
        "summary": "可供参考", "strengths": [], "weaknesses": [], "suggestions": [],
        "competency_assessment": {
            "technical": {
                "score": 80,
                "evidence": "分析任务情况再做对应的第0项处理",
                "observation": "给出了步骤", "limitations": "应人工确认",
            },
            "communication": {
                "score": 98,
                "evidence": "候选人拥有卓越的沟通能力和国际项目领导经验",
                "observation": "夸大断言", "limitations": "无",
            },
        },
    }
    
    monkeypatch.setattr(
        evaluation_service,
        "llm",
        SimpleNamespace(
            invoke=lambda messages: SimpleNamespace(
                content=json.dumps(fake_output)
            )
        ),
    )
    report = evaluation_service.generate_evaluation(
        "Python 后端", "中等", make_history(3),
        requirements="FastAPI", structured=True,
    )
    assert report.competency_assessment["dimensions"]["technical"]["score"] == 80
    assert report.competency_assessment["dimensions"]["communication"]["score"] is None
    assert report.competency_assessment["dimensions"]["learning"]["score"] is None
    assert report.competency_assessment["dimensions"]["execution"]["score"] is None


def test_competency_question_has_fixed_stage_and_only_one_reply(monkeypatch):
    from app.services import agent_service
    captured = []

    def fake_invoke(messages):
        captured.extend(messages)
        return SimpleNamespace(content="你会如何跟产品经理澄清不清晰的需求？")

    
    monkeypatch.setattr(
        agent_service,
        "llm",
        SimpleNamespace(invoke=fake_invoke),
    )
    result = agent_service.generate_competency_question_agent(
        "Python 后端", "中等", "熟悉 FastAPI",
        "communication_intro", make_history(2),
    )
    assert "澄清" in result
    assert "沟通能力" in captured[0].content
    assert "熟悉 FastAPI" in captured[0].content
    with pytest.raises(ValueError):
        agent_service.generate_competency_question_agent(
            "Python 后端", "中等", None, "technical_intro", [],
        )
