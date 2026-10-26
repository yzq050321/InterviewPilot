import os
import bcrypt

from dotenv import load_dotenv

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()
def hash_password(password: str) -> str:
    """将管理员密码转换成安全的哈希值。"""
    password_bytes = password.encode("utf-8")

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed.decode("utf-8")


def verify_password(
    password: str,
    password_hash: str
) -> bool:
    """验证输入的密码是否正确。"""
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8")
    )
    
    

def authenticate_admin(username: str, password: str) -> bool:
    """验证 HR 管理员账号和密码。"""

    # .env 已在模块加载时读取；不要在每次请求时恢复已移除的环境变量。
    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH")

    # 缺少配置时，拒绝登录
    if not admin_username or not admin_password_hash:
        return False

    # 先验证账号
    if username != admin_username:
        return False

    # 再验证密码
    try:
        return verify_password(password, admin_password_hash)
    except ValueError:
        return False
    
    

def create_admin_token() -> str:
    """生成有效期为 2 小时的 HR 管理员登录 Token。"""

    secret = os.getenv("ADMIN_JWT_SECRET")

    if not secret or len(secret) < 32:
        raise RuntimeError("ADMIN_JWT_SECRET 未正确配置")

    now = datetime.now(timezone.utc)

    payload = {
        "sub": "admin",
        "role": "admin",
        "iat": now,
        "exp": now + timedelta(hours=2),
    }

    return jwt.encode(
        payload,
        secret,
        algorithm="HS256",
    )


def verify_admin_token(token: str) -> bool:
    """验证 HR 管理员 Token 是否有效。"""

    secret = os.getenv("ADMIN_JWT_SECRET")

    if not secret or len(secret) < 32:
        return False

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "role", "iat", "exp"]},
        )

        if payload.get("role") == "admin":
            return payload.get("sub") == "admin"
        # V2.3: invited HR accounts use role="hr" and a numeric subject.
        # Status/revocation is checked at login; tokens expire after 2 hours.
        if payload.get("role") == "hr":
            return bool(payload.get("sub")) and bool(payload.get("email"))
        return False

    except jwt.InvalidTokenError:
        return False
    
    

# 从请求的 Authorization 请求头中提取 Bearer Token
admin_bearer = HTTPBearer(auto_error=False)


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_bearer),
) -> None:
    """验证当前请求是否具有 HR 权限（环境管理员或受邀 HR 账号）。"""

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="请先登录管理员账号",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_admin_token(credentials.credentials):
        raise HTTPException(
            status_code=401,
            detail="登录已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

# 演示账户仅在显式配置 DEMO_USERNAME / DEMO_PASSWORD_HASH 时启用。
# 绝不使用默认口令，也绝不复用真实管理员的凭证。
def authenticate_demo(username: str, password: str) -> bool:
    demo_username = os.getenv("DEMO_USERNAME")
    demo_password_hash = os.getenv("DEMO_PASSWORD_HASH")
    admin_username = os.getenv("ADMIN_USERNAME")
    if (
        not demo_username or not demo_password_hash
        or demo_username == admin_username or username != demo_username
    ):
        return False
    try:
        return verify_password(password, demo_password_hash)
    except ValueError:
        return False


def create_demo_token() -> str:
    secret = os.getenv("ADMIN_JWT_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("ADMIN_JWT_SECRET 未正确配置")
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": "demo", "role": "demo", "iat": now, "exp": now + timedelta(hours=2)},
        secret, algorithm="HS256",
    )


def verify_demo_token(token: str) -> bool:
    # 关掉 Demo 账号配置即可让尚未过期的 Demo JWT 立即失效。
    demo_username = os.getenv("DEMO_USERNAME")
    if not demo_username or not os.getenv("DEMO_PASSWORD_HASH") or demo_username == os.getenv("ADMIN_USERNAME"):
        return False
    secret = os.getenv("ADMIN_JWT_SECRET")
    if not secret or len(secret) < 32:
        return False
    try:
        payload = jwt.decode(
            token, secret, algorithms=["HS256"],
            options={"require": ["sub", "role", "iat", "exp"]},
        )
        return payload.get("sub") == "demo" and payload.get("role") == "demo"
    except jwt.InvalidTokenError:
        return False


def require_demo(
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_bearer),
) -> None:
    """Demo 令牌只能调用只读演示接口，不能访问真实 HR API。"""
    if credentials is None or not verify_demo_token(credentials.credentials):
        raise HTTPException(
            status_code=401, detail="演示账号未登录或登录已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
