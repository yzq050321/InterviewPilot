"""Invite-only HR account helpers.

Accounts are stored in MySQL; the existing env-based admin account remains
available as a break-glass/primary account. Registration is gated by
HR_SIGNUP_INVITE_CODE, not open to the public.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import re

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admin_auth import hash_password, verify_password
from app.models import HRUser


EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72


def normalize_email(email: str) -> str:
    return email.strip().lower()


def valid_email(email: str) -> bool:
    return len(email) <= 255 and bool(EMAIL_RE.fullmatch(email))


def password_error(password: str) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"密码至少 {MIN_PASSWORD_LENGTH} 位"
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return "密码过长，请控制在 72 个字节以内"
    return None


def create_hr_user(db: Session, *, email: str, password: str) -> HRUser:
    user = HRUser(
        email=normalize_email(email),
        password_hash=hash_password(password),
        role="hr",
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_hr(db: Session, email: str, password: str) -> HRUser | None:
    normalized = normalize_email(email)
    user = db.scalar(select(HRUser).where(HRUser.email == normalized))
    if user is None or user.status != "active":
        return None
    try:
        if not verify_password(password, user.password_hash):
            return None
    except ValueError:
        return None
    user.last_login_at = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        db.commit()
    except Exception:
        db.rollback()
    return user


def create_hr_token(user: HRUser) -> str:
    secret = os.getenv("ADMIN_JWT_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("ADMIN_JWT_SECRET 未正确配置")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": "hr",
        "email": user.email,
        "iat": now,
        "exp": now + timedelta(hours=2),
    }
    return jwt.encode(payload, secret, algorithm="HS256")
