"""V2.3 invite-only HR registration and trial applications.

No open registration: a valid HR_SIGNUP_INVITE_CODE is required. Trial
requests are stored for manual follow-up and do not create an account.
"""
from __future__ import annotations

import hmac
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin_auth import require_admin
from app.database import get_db
from app.hr_auth import (
    create_hr_token,
    create_hr_user,
    normalize_email,
    password_error,
    valid_email,
)
from app.models import HRUser, TrialRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["HR受邀注册与试用申请"])


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    invite_code: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def email_is_valid(cls, value: str) -> str:
        value = normalize_email(value)
        if not valid_email(value):
            raise ValueError("请输入有效邮箱")
        return value


class TrialRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    company: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=1000)

    @field_validator("name", "email", "company", "note")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def email_is_valid(cls, value: str) -> str:
        value = normalize_email(value)
        if not valid_email(value):
            raise ValueError("请输入有效邮箱")
        return value


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_hr(request: RegisterRequest, db: Session = Depends(get_db)):
    expected = os.getenv("HR_SIGNUP_INVITE_CODE", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="受邀注册暂未开启，请联系管理员")
    if not hmac.compare_digest(request.invite_code.strip(), expected):
        raise HTTPException(status_code=403, detail="受邀码无效")

    error = password_error(request.password)
    if error:
        raise HTTPException(status_code=422, detail=error)

    existing = db.scalar(select(HRUser.id).where(HRUser.email == request.email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")

    try:
        user = create_hr_user(db, email=request.email, password=request.password)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="该邮箱已注册，请直接登录")
    except Exception:
        db.rollback()
        logger.exception("HR 受邀注册失败")
        raise HTTPException(status_code=500, detail="注册失败，请稍后重试")

    return {
        "access_token": create_hr_token(user),
        "token_type": "bearer",
        "expires_in": 7200,
        "role": "hr",
        "email": user.email,
    }


@router.post("/trial-request", status_code=status.HTTP_202_ACCEPTED)
def submit_trial_request(request: TrialRequestCreate, db: Session = Depends(get_db)):
    item = TrialRequest(
        name=request.name,
        email=request.email,
        company=request.company or None,
        note=request.note or None,
        status="pending",
    )
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except Exception:
        db.rollback()
        logger.exception("试用申请保存失败")
        raise HTTPException(status_code=500, detail="提交失败，请稍后重试")
    return {"message": "申请已收到，我们会通过邮箱联系你", "request_id": item.id}


admin_router = APIRouter(prefix="/api/admin", tags=["HR试用申请管理"])


@admin_router.get("/trial-requests")
def list_trial_requests(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    items = db.scalars(
        select(TrialRequest).order_by(TrialRequest.id.desc()).limit(100)
    ).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "email": item.email,
            "company": item.company,
            "note": item.note,
            "status": item.status,
            "created_at": item.created_at,
        }
        for item in items
    ]
