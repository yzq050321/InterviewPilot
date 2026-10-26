"""InterviewPilot V2: HR job postings and invitation-based interviews.

Only job metadata may be fetched with an invitation code. The HR endpoints
reuse the existing `require_admin` JWT dependency. AI answers and HR reports
are not exposed here.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from openai import APITimeoutError
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin_auth import require_admin
from app.candidate_auth import create_candidate_token
from app.database import get_db
from app.models import Interview, JobPosting, Message
from app.interview_create_limiter import require_create_capacity
from app.resume_service import MAX_RESUME_BYTES, ResumeParseError, extract_resume_text
from app.services.agent_service import generate_question_agent
from app.model_usage import model_usage_scope, link_interview_to_trace

logger = logging.getLogger(__name__)
router = APIRouter(tags=["HR招聘任务与面试邀请"])


class CreateJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    position: str = Field(min_length=1, max_length=100)
    requirements: str = Field(min_length=1, max_length=2000)
    difficulty: Literal["简单", "中等", "困难"] = "中等"
    invite_valid_days: Literal[7, 14, 30] = 7

    @field_validator("title", "position", "requirements")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("该字段不能为空")
        return value


class InvitationInterviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_name: str = Field(min_length=1, max_length=100)

    @field_validator("candidate_name")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("候选人姓名不能为空")
        return value


def _utc_now() -> datetime:
    # MySQL DATETIME 无时区：统一按 UTC 写入与比较。
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _invitation_expired(job: JobPosting, *, now: datetime | None = None) -> bool:
    # 迁移后现有岗位会有 7 天宽限期；NULL 防御性地视为不可用。
    cutoff = now if now is not None else _utc_now()
    return job.invite_expires_at is None or job.invite_expires_at <= cutoff


def _require_invitation_open(job: JobPosting | None) -> JobPosting:
    if job is None or not job.is_active:
        raise HTTPException(status_code=404, detail="面试邀请无效或已停用")
    if _invitation_expired(job):
        raise HTTPException(status_code=410, detail="面试邀请已过期，请联系招聘方获取新邀请")
    return job


def _job_dict(job: JobPosting, *, include_invitation: bool = False) -> dict:
    item = {
        "job_id": job.id,
        "title": job.title,
        "position": job.position,
        "requirements": job.requirements,
        "difficulty": job.difficulty,
        "is_active": job.is_active,
        "created_at": job.created_at,
        "invite_expires_at": job.invite_expires_at,
    }
    if include_invitation:
        item["invite_code"] = job.invite_code
        item["invite_path"] = f"/invite/{job.invite_code}"
    return item


@router.post("/api/admin/jobs", status_code=status.HTTP_201_CREATED)
def create_job(
    request: CreateJobRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Only an authenticated HR admin may issue new invitation links."""
    job = JobPosting(
        title=request.title,
        position=request.position,
        requirements=request.requirements,
        difficulty=request.difficulty,
        invite_code=secrets.token_urlsafe(24),
        is_active=True,
        invite_expires_at=_utc_now() + timedelta(days=request.invite_valid_days),
    )
    try:
        db.add(job)
        db.commit()
        db.refresh(job)
    except IntegrityError:
        db.rollback()
        # Extremely rare token collision; do not reveal database details.
        raise HTTPException(status_code=409, detail="邀请码冲突，请重试")
    except Exception:
        db.rollback()
        logger.exception("创建招聘任务失败")
        raise HTTPException(status_code=500, detail="创建招聘任务失败")
    return _job_dict(job, include_invitation=True)


@router.get("/api/admin/jobs")
def list_jobs(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    jobs = db.scalars(select(JobPosting).order_by(JobPosting.id.desc())).all()
    return [_job_dict(job, include_invitation=True) for job in jobs]


@router.patch("/api/admin/jobs/{job_id}/deactivate")
def deactivate_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    job = db.get(JobPosting, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="招聘任务不存在")
    job.is_active = False
    try:
        db.commit()
        db.refresh(job)
    except Exception:
        db.rollback()
        logger.exception("停用招聘任务失败")
        raise HTTPException(status_code=500, detail="停用招聘任务失败")
    return _job_dict(job, include_invitation=True)


@router.get("/api/job-invitations/{invite_code}")
def get_job_invitation(
    invite_code: str,
    db: Session = Depends(get_db),
):
    """A holder of a valid invitation can see public job details only."""
    job = db.scalar(
        select(JobPosting).where(
            JobPosting.invite_code == invite_code,
            JobPosting.is_active.is_(True),
        )
    )
    job = _require_invitation_open(job)
    return {
        "title": job.title,
        "position": job.position,
        "requirements": job.requirements,
        "difficulty": job.difficulty,
    }


@router.post(
    "/api/job-invitations/{invite_code}/interviews/with-resume",
    status_code=status.HTTP_201_CREATED,
)
async def create_invited_interview_with_resume(
    invite_code: str,
    candidate_name: str = Form(...),
    consent: bool = Form(...),
    resume: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Create an invited interview grounded in an uploaded resume.

    The original file is read into memory, parsed, and discarded. Only extracted
    text + filename + consent timestamp are stored.
    """
    name = candidate_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="候选人姓名不能为空")
    if len(name) > 100:
        raise HTTPException(status_code=422, detail="候选人姓名不能超过 100 个字符")
    if not consent:
        raise HTTPException(status_code=422, detail="请先阅读并同意简历使用说明")

    job = db.scalar(
        select(JobPosting).where(
            JobPosting.invite_code == invite_code,
            JobPosting.is_active.is_(True),
        )
    )
    job = _require_invitation_open(job)

    job_id, position, difficulty = job.id, job.position, job.difficulty
    requirements = job.requirements

    # 解析和 AI 调用前先限流，避免共享邀请码被刷。
    require_create_capacity(invite_code=invite_code)

    filename = resume.filename
    try:
        raw = await resume.read(MAX_RESUME_BYTES + 1)
    finally:
        await resume.close()
    if len(raw) > MAX_RESUME_BYTES:
        raise HTTPException(status_code=413, detail="简历文件不能超过 5 MB")

    try:
        parsed = await run_in_threadpool(extract_resume_text, filename, raw)
    except ResumeParseError as exc:
        code = 413 if "5 MB" in str(exc) else 400
        raise HTTPException(status_code=code, detail=str(exc)) from exc

    try:
        with model_usage_scope(stage="first_question", job_id=job_id) as usage_trace:
            question = await run_in_threadpool(
                generate_question_agent,
                position,
                difficulty,
                requirements,
                parsed.text,
            )
    except APITimeoutError:
        logger.exception("简历面试首次提问超时")
        raise HTTPException(status_code=504, detail="AI 服务响应超时，请稍后重试")
    except Exception:
        logger.exception("简历面试首次提问失败")
        raise HTTPException(status_code=502, detail="AI 面试题生成失败")

    # Recheck before recording: HR may have disabled/expired the job during parsing/AI.
    job = db.scalar(
        select(JobPosting)
        .where(JobPosting.id == job_id, JobPosting.is_active.is_(True))
        .execution_options(populate_existing=True)
    )
    if job is None:
        raise HTTPException(status_code=409, detail="该招聘任务已停用")
    if _invitation_expired(job):
        raise HTTPException(status_code=410, detail="面试邀请已过期，请联系招聘方获取新邀请")

    candidate_token, token_hash = create_candidate_token()
    interview = Interview(
        job_id=job_id,
        candidate_name=name,
        candidate_token_hash=token_hash,
        position=position,
        difficulty=difficulty,
        status="in_progress",
        resume_text=parsed.text,
        resume_filename=parsed.filename,
        resume_consent_at=_utc_now(),
    )
    try:
        db.add(interview)
        db.flush()
        first_message = Message(interview_id=interview.id, role="assistant", content=question)
        db.add(first_message)
        db.flush()
        db.commit()
        link_interview_to_trace(usage_trace, interview.id)
        db.refresh(interview)
    except Exception:
        db.rollback()
        logger.exception("保存简历面试失败")
        raise HTTPException(status_code=500, detail="保存面试记录失败")

    return {
        "interview_id": interview.id,
        "interview_token": candidate_token,
        "candidate_name": interview.candidate_name,
        "position": interview.position,
        "difficulty": interview.difficulty,
        "question": question,
        "question_id": first_message.id,
        "has_resume": True,
        "resume_filename": parsed.filename,
        "resume_chars": len(parsed.text),
        "resume_pages": parsed.pages,
    }


@router.post(
    "/api/job-invitations/{invite_code}/interviews",
    status_code=status.HTTP_201_CREATED,
)
async def create_invited_interview(
    invite_code: str,
    request: InvitationInterviewRequest,
    db: Session = Depends(get_db),
):
    """Candidates cannot select the position/difficulty or read HR results."""
    job = db.scalar(
        select(JobPosting).where(
            JobPosting.invite_code == invite_code,
            JobPosting.is_active.is_(True),
        )
    )
    job = _require_invitation_open(job)

    # The candidate does not control these values.
    job_id, position, difficulty = job.id, job.position, job.difficulty
    requirements = job.requirements

    # AI 调用前执行限流，既减少费用风险，也保护共享邀请码。
    require_create_capacity(invite_code=invite_code)

    try:
        with model_usage_scope(stage="first_question", job_id=job_id) as usage_trace:
            question = await run_in_threadpool(
                generate_question_agent, position, difficulty, requirements
            )
    except APITimeoutError:
        logger.exception("邀请面试首次提问超时")
        raise HTTPException(status_code=504, detail="AI 服务响应超时，请稍后重试")
    except Exception:
        logger.exception("邀请面试首次提问失败")
        raise HTTPException(status_code=502, detail="AI 面试题生成失败")

    # Recheck before recording: HR may have disabled the job during AI call.
    job = db.scalar(
        select(JobPosting)
        .where(JobPosting.id == job_id, JobPosting.is_active.is_(True))
        .execution_options(populate_existing=True)
    )
    if job is None:
        raise HTTPException(status_code=409, detail="该招聘任务已停用")
    if _invitation_expired(job):
        raise HTTPException(status_code=410, detail="面试邀请已过期，请联系招聘方获取新邀请")

    candidate_token, token_hash = create_candidate_token()
    interview = Interview(
        job_id=job_id,
        candidate_name=request.candidate_name,
        candidate_token_hash=token_hash,
        position=position,
        difficulty=difficulty,
        status="in_progress",
    )
    try:
        db.add(interview)
        db.flush()
        first_message = Message(interview_id=interview.id, role="assistant", content=question)
        db.add(first_message)
        db.flush()
        db.commit()
        link_interview_to_trace(usage_trace, interview.id)
        db.refresh(interview)
    except Exception:
        db.rollback()
        logger.exception("保存邀请面试失败")
        raise HTTPException(status_code=500, detail="保存面试记录失败")

    # The raw candidate token is returned only once and never put into a URL.
    return {
        "interview_id": interview.id,
        "interview_token": candidate_token,
        "candidate_name": interview.candidate_name,
        "position": interview.position,
        "difficulty": interview.difficulty,
        "question": question,
        "question_id": first_message.id,
    }
