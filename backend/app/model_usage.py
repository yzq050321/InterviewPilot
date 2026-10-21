"""Privacy-preserving per-call LLM usage telemetry for InterviewPilot V2.1.

Opt-in: MODEL_USAGE_ENABLED=1. This module records counts, stage, optional
interview/job IDs and timing only. Never log message bodies, credentials,
invitation codes or raw API responses. Prices are manual estimates, not bills.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import logging
import os
from pathlib import Path
import threading
import time
from typing import Any
from uuid import uuid4

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)
_CONTEXT: ContextVar[dict | None] = ContextVar("interviewpilot_llm_usage", default=None)


def _enabled() -> bool:
    return os.getenv("MODEL_USAGE_ENABLED", "0").strip().lower() in ("1", "true", "yes", "on")


def _default_log_path() -> Path:
    return Path(os.path.expanduser("~")) / ".interviewpilot" / "model_usage.jsonl"


def _price(raw: str | None) -> Decimal | None:
    if raw is None or not raw.strip():
        return None
    try:
        rate = Decimal(raw)
        return rate if rate.is_finite() and rate >= 0 else None
    except InvalidOperation:
        return None


def _tokens(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        n = int(value)
        return n if n >= 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def _field(data: Any, *names: str) -> Any:
    if not isinstance(data, dict):
        return None
    for name in names:
        if name in data and data[name] is not None:
            return data[name]
    return None


def _usage_from_llm_result(response: Any) -> tuple[int | None, int | None, str | None]:
    """Read LangChain AIMessage.usage_metadata then provider fallback.

    We use only metadata counts; never deserialize or log generated content.
    """
    model = None
    metadata = None
    generations = getattr(response, "generations", None) or []
    if generations and generations[0]:
        message = getattr(generations[0][0], "message", None)
        if message is not None:
            metadata = getattr(message, "usage_metadata", None)
            provider_meta = getattr(message, "response_metadata", None) or {}
            model = _field(provider_meta, "model_name", "model")
            if metadata:
                return (
                    _tokens(_field(metadata, "input_tokens", "prompt_tokens")),
                    _tokens(_field(metadata, "output_tokens", "completion_tokens")),
                    str(model) if model else None,
                )
            # ChatOpenAI may keep usage here depending on provider/version.
            metadata = _field(provider_meta, "token_usage", "usage")
    output = getattr(response, "llm_output", None) or {}
    metadata = metadata or _field(output, "token_usage", "usage") or {}
    model = model or _field(output, "model_name", "model")
    return (
        _tokens(_field(metadata, "input_tokens", "prompt_tokens")),
        _tokens(_field(metadata, "output_tokens", "completion_tokens")),
        str(model) if model else None,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _append_event(record: dict, path: Path) -> None:
    """Append exactly one modest-sized JSONL record using O_APPEND.

    No candidate text or secret-bearing objects are accepted by callers.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    fd = os.open(str(path), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)


@contextmanager
def model_usage_scope(*, stage: str, interview_id: int | None = None, job_id: int | None = None):
    """Tag model calls inside a single request (also copied into threadpool)."""
    context = {
        "trace_id": uuid4().hex,
        "stage": stage,
        "interview_id": interview_id,
        "job_id": job_id,
    }
    token = _CONTEXT.set(context)
    try:
        yield context["trace_id"]
    finally:
        _CONTEXT.reset(token)


class UsageCallback(BaseCallbackHandler):
    """Capture both a tool-decision LLM call and final-answer LLM call."""

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        log_path: str | Path | None = None,
        input_cny_per_m: str | None = None,
        output_cny_per_m: str | None = None,
    ) -> None:
        self.enabled = _enabled() if enabled is None else enabled
        self.log_path = Path(log_path or os.getenv("MODEL_USAGE_LOG_PATH") or _default_log_path())
        self.input_rate = _price(
            input_cny_per_m if input_cny_per_m is not None else os.getenv("MODEL_INPUT_CNY_PER_M")
        )
        self.output_rate = _price(
            output_cny_per_m if output_cny_per_m is not None else os.getenv("MODEL_OUTPUT_CNY_PER_M")
        )
        self._running: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()

    def _begin(self, run_id: Any) -> None:
        if not self.enabled:
            return
        context = dict(_CONTEXT.get() or {})
        with self._lock:
            self._running[str(run_id)] = (time.perf_counter(), context)

    def on_chat_model_start(self, serialized: dict, messages: list, *, run_id: Any, **kwargs: Any) -> None:
        self._begin(run_id)

    def on_llm_start(self, serialized: dict, prompts: list, *, run_id: Any, **kwargs: Any) -> None:
        self._begin(run_id)

    def _finish(self, run_id: Any, *, status: str, response: Any = None) -> None:
        if not self.enabled:
            return
        with self._lock:
            running = self._running.pop(str(run_id), None)
        if running is None:
            start, context = time.perf_counter(), dict(_CONTEXT.get() or {})
        else:
            start, context = running
        used_in, used_out, model = _usage_from_llm_result(response) if response is not None else (None, None, None)
        cost = None
        if used_in is not None and used_out is not None and self.input_rate is not None and self.output_rate is not None:
            cost = (Decimal(used_in) * self.input_rate + Decimal(used_out) * self.output_rate) / Decimal(1_000_000)
        record = {
            "kind": "llm_usage",
            "timestamp_utc": _now(),
            "trace_id": context.get("trace_id"),
            "stage": context.get("stage", "unscoped"),
            "interview_id": context.get("interview_id"),
            "job_id": context.get("job_id"),
            "run_id": str(run_id),
            "status": status,
            "model": model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            "input_tokens": used_in,
            "output_tokens": used_out,
            "elapsed_ms": round((time.perf_counter() - start) * 1000),
            "estimated_cny": str(cost) if cost is not None else None,
        }
        try:
            _append_event(record, self.log_path)
        except OSError:
            # Telemetry must never break interview flow or cause a retry/bill.
            logger.warning("无法写入模型用量日志", exc_info=True)

    def on_llm_end(self, response: Any, *, run_id: Any, **kwargs: Any) -> None:
        try:
            self._finish(run_id, status="ok", response=response)
        except Exception:
            # A telemetry bug must never fail a successful, billable model call.
            logger.warning("模型用量统计失败（面试请求不受影响）", exc_info=True)

    def on_llm_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
        # Failed calls can still consume tokens. Unknown counts remain null.
        try:
            self._finish(run_id, status="error")
        except Exception:
            logger.warning("模型失败用量统计失败（面试请求不受影响）", exc_info=True)


usage_callback = UsageCallback()


def link_interview_to_trace(trace_id: str, interview_id: int) -> None:
    """After DB commit, attribute pre-create calls to the new interview ID."""
    if not usage_callback.enabled:
        return
    try:
        _append_event({
            "kind": "interview_link", "timestamp_utc": _now(),
            "trace_id": trace_id, "interview_id": interview_id,
        }, usage_callback.log_path)
    except OSError:
        logger.warning("无法记录用量追踪关联", exc_info=True)
