"""HR-managed recruitment stages and append-only follow-up log.

Never calls AI, never changes interview review_status or candidate credentials.
Demo JWT cannot access any endpoint in this router.
"""
from __future__ import annotations
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin_auth import require_admin
from app.database import get_db
from app.models import Interview, InterviewFollowup

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["招聘阶段与人工跟进"], dependencies=[Depends(require_admin)])

Stage = Literal["new", "contact", "next_round", "decision", "closed"]
STAGES = frozenset({"new", "contact", "next_round", "decision", "closed"})

class FollowupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stage: Stage
    note: str = Field(min_length=1, max_length=1000)

    @field_validator("note")
    @classmethod
    def validate_note(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("跟进备注不能为空")
        return value


def _followup_dict(item: InterviewFollowup) -> dict:
    return {
        "id": item.id,
        "interview_id": item.interview_id,
        "old_stage": item.old_stage,
        "new_stage": item.new_stage,
        "note": item.note,
        "created_at": item.created_at,
    }


@router.get("/pipeline")
def pipeline_overview(db: Session = Depends(get_db)):
    """Small list for the HR workspace, stage keyed by interview ID."""
    rows = db.execute(select(Interview.id, Interview.recruitment_stage)).all()
    return [{"interview_id": iid, "stage": stage} for iid, stage in rows]


@router.get("/interviews/{interview_id}/pipeline")
def pipeline_detail(interview_id: int, db: Session = Depends(get_db)):
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=404, detail="面试不存在")
    history = db.scalars(
        select(InterviewFollowup).where(InterviewFollowup.interview_id == interview_id)
        .order_by(InterviewFollowup.id.desc())
    ).all()
    return {"interview_id": interview.id, "stage": interview.recruitment_stage,
            "history": [_followup_dict(item) for item in history]}


@router.post("/interviews/{interview_id}/pipeline")
def save_followup(interview_id: int, payload: FollowupCreate, db: Session = Depends(get_db)):
    """Lock interview, append note and update stage in one DB transaction."""
    interview = db.scalar(
        select(Interview).where(Interview.id == interview_id).with_for_update()
    )
    if interview is None:
        raise HTTPException(status_code=404, detail="面试不存在")
    previous = interview.recruitment_stage
    # Note-only entries are intentional and preserve an audit trail.
    entry = InterviewFollowup(interview_id=interview.id, old_stage=previous,
                              new_stage=payload.stage, note=payload.note)
    interview.recruitment_stage = payload.stage
    db.add(entry)
    try:
        db.commit()
        db.refresh(entry)
    except Exception:
        db.rollback()
        logger.exception("保存招聘跟进失败，面试编号=%s", interview_id)
        raise HTTPException(status_code=500, detail="保存招聘跟进失败")
    return {"interview_id": interview.id, "stage": interview.recruitment_stage,
            "followup": _followup_dict(entry)}
