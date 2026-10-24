"""No-network tests for opt-in model usage auditing (no real LLM calls)."""
from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import app.model_usage as usage


def fake_result(input_tokens=22, output_tokens=11, model="test-model"):
    message = SimpleNamespace(usage_metadata={"input_tokens": input_tokens, "output_tokens": output_tokens},
                              response_metadata={"model_name": model}, content="DONOTLOG")
    return SimpleNamespace(generations=[[SimpleNamespace(message=message)]], llm_output={})


def read_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_two_calls_per_agent_and_trace_mapping(tmp_path, monkeypatch):
    path = tmp_path / "model_usage.jsonl"
    callback = usage.UsageCallback(enabled=True, log_path=path, input_cny_per_m="1", output_cny_per_m="2")
    monkeypatch.setattr(usage, "usage_callback", callback)
    with usage.model_usage_scope(stage="first_question", job_id=3) as trace:
        for _ in range(2):
            run = uuid4()
            callback.on_chat_model_start({}, [], run_id=run)
            callback.on_llm_end(fake_result(), run_id=run)
    usage.link_interview_to_trace(trace, interview_id=99)
    events = read_events(path)
    assert [r["kind"] for r in events] == ["llm_usage", "llm_usage", "interview_link"]
    assert events[0]["stage"] == "first_question"
    assert events[1]["job_id"] == 3
    assert events[0]["interview_id"] is None
    assert events[2]["interview_id"] == 99
    assert all(r.get("estimated_cny") == "0.000044" for r in events[:2])
    assert "DONOTLOG" not in path.read_text(encoding="utf-8")


def test_failure_has_unknown_usage_not_fake_zero(tmp_path):
    path = tmp_path / "calls.jsonl"
    callback = usage.UsageCallback(enabled=True, log_path=path, input_cny_per_m="1", output_cny_per_m="2")
    with usage.model_usage_scope(stage="evaluation", interview_id=7):
        rid = uuid4()
        callback.on_llm_start({}, [], run_id=rid)
        callback.on_llm_error(RuntimeError("SENSITIVE_EXCEPTION_DO_NOT_LOG"), run_id=rid)
    row = read_events(path)[0]
    assert row["interview_id"] == 7
    assert row["status"] == "error"
    assert row["input_tokens"] is None
    assert row["output_tokens"] is None
    assert row["estimated_cny"] is None
    assert "SENSITIVE_EXCEPTION_DO_NOT_LOG" not in path.read_text(encoding="utf-8")


def test_disabled_does_not_write(tmp_path):
    path = tmp_path / "disabled.jsonl"
    callback = usage.UsageCallback(enabled=False, log_path=path)
    callback.on_llm_start({}, [], run_id=uuid4())
    callback.on_llm_end(fake_result(), run_id=uuid4())
    assert not path.exists()


def test_fallback_openai_token_usage():
    msg = SimpleNamespace(usage_metadata=None, response_metadata={})
    res = SimpleNamespace(generations=[[SimpleNamespace(message=msg)]],
                          llm_output={"token_usage": {"prompt_tokens": 10, "completion_tokens": 4},
                                      "model_name": "fallback"})
    assert usage._usage_from_llm_result(res) == (10, 4, "fallback")


def test_context_restores_on_nested_scopes():
    assert usage._CONTEXT.get() is None
    with usage.model_usage_scope(stage="outer", interview_id=1):
        assert usage._CONTEXT.get()["interview_id"] == 1
        with usage.model_usage_scope(stage="inner", interview_id=2):
            assert usage._CONTEXT.get()["interview_id"] == 2
        assert usage._CONTEXT.get()["interview_id"] == 1
    assert usage._CONTEXT.get() is None
