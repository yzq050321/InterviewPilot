"""One authoritative workflow for candidate-triggered and HR-triggered evaluation.

The DB atomically claims the generation slot *before* calling the model. This
prevents duplicate AI billing in concurrent requests, including across workers.
A stale slot is reclaimable after a worker crash (15 minute lease).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Evaluation, Interview, JobPosting, Message
from app.model_usage import model_usage_scope

logger = logging.getLogger(__name__)
LEASE_MINUTES = 15


def utc_naive() -> datetime:
    """Store naive UTC datetimes compatible with MySQL DATETIME."""
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def get_evaluation_state(interview: Interview, has_report: bool) -> str:
    """Report existence takes precedence for old records and stale flags."""
    if has_report:
        return "ready"
    if interview.status != "completed":
        return "not_started"
    if interview.evaluation_state == "generating":
        stamp = interview.evaluation_started_at
        if not stamp or stamp < utc_naive() - timedelta(minutes=LEASE_MINUTES):
            return "failed"
        return "generating"
    if interview.evaluation_state == "failed":
        return "failed"
    return "pending"


def _fail_claim(interview_id: int, stamp: datetime, reason: str, session_factory: Callable) -> None:
    """Only the currently owning attempt can update failure state."""
    try:
        with session_factory() as db:
            db.execute(
                update(Interview).where(
                    Interview.id == interview_id,
                    Interview.evaluation_state == "generating",
                    Interview.evaluation_started_at == stamp,
                ).values(evaluation_state="failed", evaluation_error=reason)
            )
            db.commit()
    except Exception:
        logger.exception("无法更新评估生成失败状态，面试编号=%s", interview_id)


async def generate_and_store_report(
    interview_id: int,
    *,
    session_factory: Callable,
    generator: Callable,
) -> dict:
    """Called only after the caller has passed candidate or admin authorization."""
    with session_factory() as db:
        interview = db.get(Interview, interview_id)
        if interview is None:
            raise HTTPException(status_code=404, detail="面试不存在")
        if interview.status != "completed":
            raise HTTPException(status_code=400, detail="请先结束面试，再生成评估报告")
        if db.scalar(select(Evaluation.id).where(Evaluation.interview_id == interview_id)) is not None:
            raise HTTPException(status_code=409, detail="该面试已有评估报告")

        messages = db.scalars(
            select(Message).where(Message.interview_id == interview_id).order_by(Message.id)
        ).all()
        history = [{"role": m.role, "content": m.content} for m in messages]
        if not any(m["role"] == "user" for m in history):
            raise HTTPException(status_code=400, detail="面试没有候选人回答，无法生成报告")

        job = db.get(JobPosting, interview.job_id) if interview.job_id is not None else None
        kwargs = {"position": interview.position, "difficulty": interview.difficulty, "history": history}
        if job and job.requirements:
            kwargs["requirements"] = job.requirements
        if interview.resume_text:
            kwargs["resume_text"] = interview.resume_text
        if interview.job_id is not None:
            kwargs["structured"] = True

        stamp = utc_naive()
        stale_cutoff = stamp - timedelta(minutes=LEASE_MINUTES)
        claim = db.execute(
            update(Interview).where(
                Interview.id == interview_id,
                Interview.status == "completed",
                or_(
                    Interview.evaluation_state.is_(None),
                    Interview.evaluation_state.in_(("pending", "failed", "ready")),
                    and_(
                        Interview.evaluation_state == "generating",
                        or_(Interview.evaluation_started_at.is_(None), Interview.evaluation_started_at < stale_cutoff),
                    ),
                ),
            ).values(evaluation_state="generating", evaluation_started_at=stamp, evaluation_error=None)
        )
        if claim.rowcount != 1:
            db.rollback()
            raise HTTPException(status_code=409, detail="报告正在生成，请稍后刷新")
        db.commit()
        job_id = interview.job_id

    try:
        with model_usage_scope(stage="evaluation", interview_id=interview_id, job_id=job_id):
            report = await run_in_threadpool(generator, **kwargs)
    except Exception:
        logger.exception("AI 评估生成失败，面试编号=%s", interview_id)
        _fail_claim(interview_id, stamp, "AI 生成失败，可重试", session_factory)
        raise HTTPException(status_code=502, detail="AI 评估生成失败，请稍后重试")

    try:
        with session_factory() as db:
            # Prevent a superseded stale worker from writing a report after a retry.
            current = db.get(Interview, interview_id)
            if not current or current.evaluation_state != "generating" or current.evaluation_started_at != stamp:
                raise HTTPException(status_code=409, detail="本次生成已被更新的请求取代")
            if db.scalar(select(Evaluation.id).where(Evaluation.interview_id == interview_id)) is not None:
                raise HTTPException(status_code=409, detail="该面试已有评估报告")
            evaluation = Evaluation(
                interview_id=interview_id,
                technical_score=report.technical_score,
                completeness_score=report.completeness_score,
                clarity_score=report.clarity_score,
                overall_score=report.overall_score,
                summary=report.summary,
                strengths=report.strengths,
                weaknesses=report.weaknesses,
                suggestions=report.suggestions,
                competency_assessment=getattr(report, "competency_assessment", None),
            )
            db.add(evaluation)
            db.flush()
            evaluation_id = evaluation.id
            current.evaluation_state = "ready"
            current.evaluation_error = None
            db.commit()
            return {
                "evaluation_id": evaluation_id,
                "interview_id": interview_id,
                "message": "评估报告生成成功",
            }
    except HTTPException:
        raise
    except IntegrityError:
        _fail_claim(interview_id, stamp, "报告并发保存冲突，可检查当前状态", session_factory)
        raise HTTPException(status_code=409, detail="报告可能已经生成，请刷新查看")
    except Exception:
        logger.exception("评估报告入库失败，面试编号=%s", interview_id)
        _fail_claim(interview_id, stamp, "报告保存失败，可重试", session_factory)
        raise HTTPException(status_code=500, detail="评估报告保存失败，请稍后重试")
