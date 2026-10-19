"""V2 轻量 AI 创建请求限流。单进程内存实现，仅适合当前演示环境。

警告：多进程、多机器或重启后不共享计数；公开上线请用 Redis/API 网关。
使用按邀请码+全局额度，避免 Nginx 反代令所有访问表现为 127.0.0.1
而造成的错误 IP 限流；不信任用户可伪造的 X-Forwarded-For。
"""

from collections import defaultdict, deque
import math
from threading import Lock
from time import monotonic

from fastapi import HTTPException


_LOCK = Lock()
_EVENTS: dict[str, deque[float]] = defaultdict(deque)


def _reserve(quota: list[tuple[str, int, int]]) -> int:
    """先检查全部额度，再原子记一次调用；返回等待秒数，0 表示成功。"""
    now = monotonic()
    with _LOCK:
        retry_after = 0
        for key, capacity, seconds in quota:
            events = _EVENTS[key]
            while events and now - events[0] >= seconds:
                events.popleft()
            if len(events) >= capacity:
                retry_after = max(retry_after, max(1, math.ceil(seconds - (now - events[0]))))
        if retry_after:
            return retry_after
        for key, _, _ in quota:
            _EVENTS[key].append(now)
        return 0


def require_create_capacity(invite_code: str | None = None) -> None:
    # 每分钟至多 30 次创建 AI 面试（传统入口+邀请入口合计）；
    # 单个邀请每分钟至多 5 次、每小时至多 20 次。
    quota = [("all_interview_creates:minute", 30, 60)]
    if invite_code is not None:
        quota.extend([
            (f"invitation:{invite_code}:minute", 5, 60),
            (f"invitation:{invite_code}:hour", 20, 3600),
        ])
    seconds = _reserve(quota)
    if seconds:
        raise HTTPException(
            status_code=429,
            detail="面试创建请求过于频繁，请稍后再试",
            headers={"Retry-After": str(seconds)},
        )
