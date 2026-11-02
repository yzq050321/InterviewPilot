"""基于 Redis 的滑动窗口限流存储。

背景
----
原先 `app/login_limiter.py` 与 `app/interview_create_limiter.py` 都是
「进程内 dict + deque」的实现：

- 单进程跑没问题；
- uvicorn 起多 worker 后，每个 worker 各有一份计数，实际限额变成 N 倍；
- 多实例部署时更是完全失效；
- 进程重启后计数清零，攻击者重启即可绕过。

这里把窗口日志搬到 Redis 的 ZSET（score = 事件发生时间），所有进程
共享同一份状态。

为什么用 ZSET 而不是 INCR
------------------------
原实现是**滑动窗口**：任意连续 N 秒内不超过 M 次。

如果换成 `INCR + EXPIRE` 的固定窗口，会在窗口边界处出现双倍突发
（第 299 秒打满、第 301 秒又打满），等于削弱了限流强度。
限流是安全相关行为，迁移存储时不应顺手改变语义。

并发安全
--------
「裁剪窗口 → 计数 → 写入」如果拆成三条独立命令，会出现 TOCTOU 竞态：
两个请求同时读到 count=limit-1，都放行，结果超发。

这里用「先加后验、超了撤回」：
    1. ZADD 占位
    2. ZCARD 取总数
    3. 超过 limit 时 ZREM 撤回自己
每一步都是 Redis 原子命令。并发下最坏情况是**误拒**（双方都撤回），
但**不会超发**。限流场景下这个偏差方向是安全的。
"""

from __future__ import annotations

import logging
import os
import time
import uuid

logger = logging.getLogger(__name__)

DEFAULT_REDIS_URL = "redis://127.0.0.1:6379/0"

_client = None
_override = None


def get_client():
    """返回 Redis 客户端。测试可通过 set_client() 注入 fakeredis。"""
    global _client
    if _override is not None:
        return _override
    if _client is None:
        import redis

        url = os.getenv("REDIS_URL") or DEFAULT_REDIS_URL
        _client = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_timeout=1,
            socket_connect_timeout=1,
        )
    return _client


def set_client(client) -> None:
    """注入自定义客户端（测试用 fakeredis）。"""
    global _override
    _override = client


def reset_client() -> None:
    """清除缓存的客户端与注入。"""
    global _client, _override
    _client = None
    _override = None


def _prefix(key: str) -> str:
    return f"ip:rl:{key}"


def reserve_many(quota: list[tuple[str, int, int]]) -> tuple[bool, int]:
    """一次性检查多条额度：全部未超限才保留占位，任一超限则全部撤回。

    这与原先 `interview_create_limiter._reserve` 的语义一致，必须保留：
    如果改成"逐条检查、逐条记账"，攻击者只要反复刷一个已满的邀请码，
    就能把全局额度（30/分钟）耗光，导致所有正常用户都被限流。

    返回 (是否放行, 建议等待秒数)。
    """
    if not quota:
        return True, 0

    client = get_client()
    now = time.time()
    reserved: list[tuple[str, str]] = []  # (full_key, member)

    try:
        # 1. 先为每条额度占一个位（member 必须唯一，否则会互相覆盖）
        for key, _limit, window in quota:
            full_key = _prefix(key)
            member = f"{now:.6f}:{uuid.uuid4().hex}"
            client.zremrangebyscore(full_key, "-inf", f"({now - window}")
            client.zadd(full_key, {member: now})
            reserved.append((full_key, member))

        # 2. 统计并判断是否全部未超限
        retry_after = 0
        for (full_key, _member), (_key, limit, window) in zip(reserved, quota):
            if int(client.zcard(full_key)) > limit:
                oldest = client.zrange(full_key, 0, 0, withscores=True)
                if oldest:
                    retry = window - (now - float(oldest[0][1]))
                    retry_after = max(retry_after, max(1, int(retry) + 1))
                else:
                    retry_after = max(retry_after, 1)

        # 3. 任一超限：撤回本次全部占位，保证"被拒绝的请求不消耗额度"
        if retry_after:
            for full_key, member in reserved:
                client.zrem(full_key, member)
            return False, retry_after

        # 4. 全部通过：设置过期时间，窗口结束后自动回收
        max_window = max(window for _key, _limit, window in quota)
        for full_key, _member in reserved:
            client.pexpire(full_key, int((max_window + 1) * 1000))
        return True, 0
    except Exception:
        # fail-open：限流是附加保护，不该因它自身故障阻断业务
        logger.exception("限流存储不可用，本次放行")
        return True, 0


def reserve(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """单条额度的滑动窗口占位。"""
    return reserve_many([(key, limit, window_seconds)])


def record_event(key: str, window_seconds: int) -> int:
    """记录一次事件并返回窗口内的事件数（用于"累计失败次数"场景）。"""
    client = get_client()
    full_key = _prefix(key)
    now = time.time()
    member = f"{now:.6f}:{uuid.uuid4().hex}"
    try:
        client.zremrangebyscore(full_key, "-inf", f"({now - window_seconds}")
        client.zadd(full_key, {member: now})
        client.pexpire(full_key, int((window_seconds + 1) * 1000))
        return int(client.zcard(full_key))
    except Exception:
        logger.exception("限流存储不可用，跳过计数：key=%s", key)
        return 0


def set_lock(key: str, ttl_seconds: int) -> None:
    """写入一个带过期时间的锁定标记。"""
    client = get_client()
    try:
        client.set(_prefix(key), "1", ex=ttl_seconds)
    except Exception:
        logger.exception("限流存储不可用，跳过加锁：key=%s", key)


def is_locked(key: str) -> bool:
    client = get_client()
    try:
        return bool(client.exists(_prefix(key)))
    except Exception:
        logger.exception("限流存储不可用，视为未锁定：key=%s", key)
        return False


def delete(*keys: str) -> None:
    if not keys:
        return
    client = get_client()
    try:
        client.delete(*[_prefix(k) for k in keys])
    except Exception:
        logger.exception("限流存储不可用，跳过删除")


def clear_namespace(prefix: str) -> int:
    """删除某个前缀下的所有键（测试重置用）。返回删除数量。"""
    client = get_client()
    pattern = _prefix(prefix) + "*"
    removed = 0
    try:
        batch = []
        for key in client.scan_iter(match=pattern, count=200):
            batch.append(key)
            if len(batch) >= 200:
                removed += client.delete(*batch)
                batch = []
        if batch:
            removed += client.delete(*batch)
    except Exception:
        logger.exception("限流存储不可用，跳过清理：prefix=%s", prefix)
    return removed
