"""HR-only review and recovery endpoints. No automatic hiring decisions."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Literal

from app.admin_auth import require_admin
from app.database import get_db, SessionLocal
from app.models import Evaluation, Interview
from app.evaluation_workflow import generate_and_store_report, get_evaluation_state, utc_naive
from app.services.evaluation_service import generate_evaluation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin/interviews", tags=["HR评估恢复与人工复核"])


class ReviewUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_status: Literal["pending", "reviewed", "follow_up"]
    review_note: str = Field(default="", max_length=1000)


@router.post("/{interview_id}/evaluation/retry")
async def retry_evaluation(interview_id: int, _: None = Depends(require_admin)):
    """Only HR may recover a missing/failed report; no candidate token required."""
    return await generate_and_store_report(
        interview_id, session_factory=SessionLocal, generator=generate_evaluation
    )


@router.patch("/{interview_id}/review")
def update_review(
    interview_id: int,
    payload: ReviewUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="面试不存在")
    if interview.status != "completed":
        raise HTTPException(status_code=409, detail="面试尚未完成，不能人工复核")
    has_report = db.scalar(select(Evaluation.id).where(Evaluation.interview_id == interview_id)) is not None
    if not has_report:
        raise HTTPException(status_code=409, detail="请先生成 AI 评估报告，再进行人工复核")
    interview.review_status = payload.review_status
    interview.review_note = payload.review_note.strip()
    interview.reviewed_at = utc_naive() if payload.review_status != "pending" else None
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("保存人工复核失败，面试编号=%s", interview_id)
        raise HTTPException(status_code=500, detail="保存人工复核失败")
    return {
        "interview_id": interview.id,
        "review_status": interview.review_status,
        "review_note": interview.review_note,
        "reviewed_at": interview.reviewed_at,
        "evaluation_status": get_evaluation_state(interview, True),
    }
