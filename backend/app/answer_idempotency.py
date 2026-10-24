"""Durable, per-question deduplication for candidate follow-up requests.

A request is reserved (committed) before any external AI call. Unique constraints
serialize competing submissions at the DB level. A timed-out caller can replay
its request_id and retrieve the committed response. The 15-minute lease offers
crash recovery but cannot guarantee exactly-once billing by an external LLM.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid5, NAMESPACE_OID

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import AnswerAttempt, Interview, Message

LEASE_SECONDS = 15 * 60


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalized_id(request_id: UUID | None, interview_id: int, question_id: int, answer: str) -> str:
    if request_id is not None:
        return str(request_id)
    # Compatibility for older clients that omit request_id. New clients MUST
    # supply question_id + request_id for reliable recovery across timeouts.
    return str(uuid5(NAMESPACE_OID, f"{interview_id}:{question_id}:{hashlib.sha256(answer.encode()).hexdigest()}"))


def response_from_attempt(attempt: AnswerAttempt) -> dict:
    return {
        "interview_id": attempt.interview_id,
        "next_question": attempt.next_question,
        "question_id": attempt.next_question_id,
        "finished_questions": attempt.next_stage == "finished",
        "interview_stage": attempt.next_stage,
        "replayed": True,
    }


def reserve_attempt(
    db: Session,
    interview: Interview,
    last_question: Message,
    request_id: UUID | None,
    expected_question_id: int | None,
    answer: str,
) -> AnswerAttempt | dict:
    """Return reserved row for execution, or completed cached response.

    On conflicts returns 409. Candidate authentication MUST precede this call.
    """
    digest = hashlib.sha256(answer.encode("utf-8")).hexdigest()
    requested_question_id = expected_question_id or last_question.id
    key = normalized_id(request_id, interview.id, requested_question_id, answer)
    existing = db.scalar(select(AnswerAttempt).where(AnswerAttempt.request_id == key))
    if existing is not None:
        if (existing.interview_id != interview.id or existing.question_id != requested_question_id
                or existing.answer_hash != digest):
            raise HTTPException(409, "提交标识与原回答不一致，请刷新面试记录")
        if existing.status == "done":
            return response_from_attempt(existing)
        if last_question.id != requested_question_id:
            raise HTTPException(409, "面试问题已变化，请刷新页面恢复")
        if interview.status != "in_progress":
            raise HTTPException(409, "面试已经结束，不能继续提交回答")
        if existing.status == "processing" and existing.started_at > utc_now() - timedelta(seconds=LEASE_SECONDS):
            raise HTTPException(409, "这道题正在处理中，请稍后使用同一次提交重试")
        # Retry a failed or stale reservation. Atomic UPDATE ensures only one
        # worker claims this request on the second attempt.
        now = utc_now()
        claimed = db.execute(
            update(AnswerAttempt).where(
                AnswerAttempt.id == existing.id,
                AnswerAttempt.status != "done",
                (AnswerAttempt.status == "failed")
                | ((AnswerAttempt.status == "processing") & (AnswerAttempt.started_at <= now - timedelta(seconds=LEASE_SECONDS))),
            ).values(status="processing", started_at=now)
        )
        if claimed.rowcount != 1:
            db.rollback()
            raise HTTPException(409, "提交仍在处理中，请稍后重试")
        db.commit()
        db.refresh(existing)
        return existing

    if last_question.id != requested_question_id:
        raise HTTPException(409, "问题已更新，请刷新面试页面后再提交")
    if interview.status != "in_progress":
        raise HTTPException(409, "当前面试已结束")
    attempt = AnswerAttempt(
        interview_id=interview.id,
        question_id=last_question.id,
        request_id=key,
        answer_hash=digest,
        status="processing",
        started_at=utc_now(),
    )
    try:
        db.add(attempt)
        db.commit()  # durable claim before external AI call
        db.refresh(attempt)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "这道题已有提交记录，请刷新面试或重试原提交")
    return attempt


def fail_attempt(db: Session, attempt: AnswerAttempt) -> None:
    try:
        db.rollback()
        db.execute(
            update(AnswerAttempt).where(
                AnswerAttempt.id == attempt.id,
                AnswerAttempt.status == "processing",
                AnswerAttempt.started_at == attempt.started_at,
            ).values(status="failed")
        )
        db.commit()
    except Exception:
        db.rollback()


def has_active_attempt(db: Session, interview_id: int) -> bool:
    # A crashed worker leaves a processing row behind. Only a non-expired
    # attempt may block "complete"; otherwise the candidate could be stuck
    # forever even though a retry is allowed after the lease.
    return db.scalar(
        select(AnswerAttempt.id).where(
            AnswerAttempt.interview_id == interview_id,
            AnswerAttempt.status == "processing",
            AnswerAttempt.started_at > utc_now() - timedelta(seconds=LEASE_SECONDS),
        ).limit(1)
    ) is not None
