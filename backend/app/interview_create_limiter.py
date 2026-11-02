"""AI 面试创建请求限流（Redis 版本）。

额度规则与旧实现一致：
- 全局：每分钟最多 30 次创建
- 单个邀请码：每分钟最多 5 次、每小时最多 20 次

为什么按邀请码而不是按 IP：Nginx 反向代理后所有请求的来源都表现为
127.0.0.1，而 `X-Forwarded-For` 可以被客户端伪造。邀请码是服务端
签发的凭证，更适合作为限流维度。

与旧实现的差异只在存储：原先用进程内 dict + deque，多 worker 各算各的；
现在状态放 Redis，所有进程共享同一份计数。
"""

from fastapi import HTTPException

from app import rate_limit

_WINDOW_MINUTE = 60
_WINDOW_HOUR = 3600


def require_create_capacity(invite_code: str | None = None) -> None:
    """检查创建额度，不足时抛 429 并带 Retry-After。"""

    quota: list[tuple[str, int, int]] = [("create:all:minute", 30, _WINDOW_MINUTE)]
    if invite_code is not None:
        quota.extend(
            [
                (f"create:inv:{invite_code}:minute", 5, _WINDOW_MINUTE),
                (f"create:inv:{invite_code}:hour", 20, _WINDOW_HOUR),
            ]
        )

    # reserve_many 保证：任一额度超限时，本次所有额度都不扣减。
    # 否则攻击者可以只刷一个已满的邀请码，把全局额度耗光。
    allowed, retry_after = rate_limit.reserve_many(quota)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="面试创建请求过于频繁，请稍后再试",
            headers={"Retry-After": str(retry_after)},
        )


def reset_state() -> None:
    """测试用：清空创建限流状态。"""

    rate_limit.clear_namespace("create:")
