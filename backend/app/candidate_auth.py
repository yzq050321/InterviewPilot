
import hashlib
import hmac
import secrets


def create_candidate_token() -> tuple[str, str]:
    """生成候选人 Token，并返回原始 Token 和哈希值。"""

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    return token, token_hash


def verify_candidate_token(
    token: str,
    stored_hash: str | None,
) -> bool:
    """验证候选人 Token 是否与数据库中的哈希匹配。"""

    if not token or not stored_hash:
        return False

    submitted_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    return hmac.compare_digest(
        submitted_hash,
        stored_hash,
    )