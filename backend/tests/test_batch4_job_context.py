"""Batch 4 prompt and limiter unit tests. Does not call real AI."""
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import agent_service
from app.services import evaluation_service
from app import interview_create_limiter as limiter


def test_first_question_prompt_has_hr_requirements(monkeypatch):
    captured = {}
    def fake_run(task):
        captured["prompt"] = task
        return "请解释 FastAPI 的依赖注入。"
    monkeypatch.setattr(agent_service, "run_interview_agent", fake_run)
    result = agent_service.generate_question_agent(
        "Python 后端开发", "中等", "必须理解 FastAPI 依赖注入"
    )
    assert result == "请解释 FastAPI 的依赖注入。"
    assert "必须理解 FastAPI 依赖注入" in captured["prompt"]
    assert "技术面试" in captured["prompt"]


def test_legacy_question_still_works(monkeypatch):
    monkeypatch.setattr(agent_service, "run_interview_agent", lambda prompt: "旧版问题")
    assert agent_service.generate_question_agent("Python", "中等") == "旧版问题"


def test_followup_receives_job_requirements(monkeypatch):
    captured = {}

    class FakeLLM:
        def invoke(self, messages):
            captured["messages"] = messages
            return SimpleNamespace(tool_calls=[], content="请说明一个 FastAPI 实战案例。")

    monkeypatch.setattr(agent_service, "llm_with_tools", FakeLLM())
    answer = agent_service.generate_followup_agent(
        "Python 开发", "中等",
        [{"role": "assistant", "content": "请自我介绍"},
         {"role": "user", "content": "我会 Python"}],
        "熟悉 FastAPI 和 SQLAlchemy",
    )
    assert "FastAPI" in captured["messages"][0].content
    assert answer.startswith("请说明")


def test_evaluation_refers_to_requirements_not_invented_evidence(monkeypatch):
    seen = {}
    class FakeLLM:
        def invoke(self, messages):
            seen["text"] = messages[1].content
            return SimpleNamespace(content=json.dumps({
                "technical_score": None, "completeness_score": None,
                "clarity_score": None, "overall_score": None,
                "summary": "证据不足", "strengths": [], "weaknesses": [],
                "suggestions": ["增加针对性面试问题"],
            }, ensure_ascii=False))
    monkeypatch.setattr(evaluation_service, "llm", FakeLLM())
    report = evaluation_service.generate_evaluation(
        "Python 后端", "中等", [{"role": "user", "content": "我还不会"}],
        requirements="需要掌握 MySQL 索引",
    )
    assert report.overall_score is None
    assert "MySQL 索引" in seen["text"]


def test_invitation_limiter_and_global_limiter():
    with limiter._LOCK:
        limiter._EVENTS.clear()
    for _ in range(5):
        limiter.require_create_capacity(invite_code="fixture-invite-code-1")
    with pytest.raises(HTTPException) as exc:
        limiter.require_create_capacity(invite_code="fixture-invite-code-1")
    assert exc.value.status_code == 429
    assert int(exc.value.headers["Retry-After"]) > 0

    # 其他邀请码仍可调用，不会被第一个邀请码的额度错误影响。
    limiter.require_create_capacity(invite_code="fixture-invite-code-2")
    with limiter._LOCK:
        limiter._EVENTS.clear()
    for _ in range(30):
        limiter.require_create_capacity()
    with pytest.raises(HTTPException) as exc:
        limiter.require_create_capacity()
    assert exc.value.status_code == 429
    with limiter._LOCK:
        limiter._EVENTS.clear()
