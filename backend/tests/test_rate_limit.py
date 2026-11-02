"""Redis 限流存储的行为测试。

重点不是"限流能挡住请求"（旧实现也能），而是：

1. 两个独立的 Redis 连接看到的是**同一份计数** —— 这正是换 Redis 的目的；
2. 窗口会随时间滑动，而不是固定窗口那样在边界双倍突发；
3. 被拒绝的请求不消耗其他额度；
4. Redis 不可用时 fail-open，不阻断业务。

fakeredis 实例由 conftest 的 autouse fixture 注入；需要"多客户端共享"
的场景在用例里自建共享 FakeServer。
"""

import fakeredis
import pytest
from fastapi import HTTPException

from app import interview_create_limiter, login_limiter, rate_limit


def _shared_clients(count: int = 2):
    """创建共享同一份数据的多个连接，模拟多个 worker 进程。"""
    server = fakeredis.FakeServer()
    return [fakeredis.FakeRedis(server=server, decode_responses=True) for _ in range(count)]


def test_reserve_allows_up_to_limit_then_rejects():
    for _ in range(3):
        assert rate_limit.reserve("basic", 3, 60)[0] is True

    allowed, retry_after = rate_limit.reserve("basic", 3, 60)
    assert allowed is False
    assert retry_after >= 1


def test_two_clients_share_one_counter():
    """两个独立连接共享计数。

    旧实现里每个 worker 各有一份 dict，限额会被放大成 worker 数倍。
    """
    a, b = _shared_clients()
    rate_limit.set_client(a)
    assert rate_limit.reserve("shared", 2, 60)[0] is True

    rate_limit.set_client(b)  # 相当于换到另一个 worker
    assert rate_limit.reserve("shared", 2, 60)[0] is True

    assert rate_limit.reserve("shared", 2, 60)[0] is False


def test_window_slides_after_expiry(monkeypatch):
    """窗口滑过之后，计数应当重新可用。"""
    now = [1000.0]
    monkeypatch.setattr(rate_limit.time, "time", lambda: now[0])

    assert rate_limit.reserve("slide", 2, 60)[0] is True
    assert rate_limit.reserve("slide", 2, 60)[0] is True
    assert rate_limit.reserve("slide", 2, 60)[0] is False

    now[0] += 61
    assert rate_limit.reserve("slide", 2, 60)[0] is True


def test_rejected_call_does_not_consume_other_quota():
    """被拒绝的请求不能消耗其他额度。

    否则攻击者只要反复刷一个已满的邀请码，就能把全局额度耗光，
    导致所有正常用户都被限流。
    """
    quota = [("global", 5, 60), ("invite", 1, 60)]
    assert rate_limit.reserve_many(quota)[0] is True

    allowed, retry_after = rate_limit.reserve_many(quota)
    assert allowed is False
    assert retry_after >= 1

    client = rate_limit.get_client()
    # 只保留了第一次成功的那条，被拒绝的那次两个额度都没留下记录
    assert int(client.zcard("ip:rl:global")) == 1
    assert int(client.zcard("ip:rl:invite")) == 1


def test_login_locks_after_five_failures():
    ip = "203.0.113.9"
    login_limiter.reset_state()

    for _ in range(4):
        login_limiter.record_login_failure(ip)
    assert login_limiter.is_login_blocked(ip) is False

    login_limiter.record_login_failure(ip)  # 第 5 次触发锁定
    assert login_limiter.is_login_blocked(ip) is True

    login_limiter.clear_login_failures(ip)
    assert login_limiter.is_login_blocked(ip) is False


def test_create_limiter_limits_single_invitation():
    interview_create_limiter.reset_state()

    for _ in range(5):
        interview_create_limiter.require_create_capacity(invite_code="inv-1")

    with pytest.raises(HTTPException) as exc:
        interview_create_limiter.require_create_capacity(invite_code="inv-1")

    assert exc.value.status_code == 429
    assert "Retry-After" in (exc.value.headers or {})


def test_redis_failure_fails_open():
    """Redis 不可用时放行，而不是把登录/建岗流程一起打断。"""

    class BrokenClient:
        def __getattr__(self, _name):
            def _raise(*_args, **_kwargs):
                raise RuntimeError("redis down")

            return _raise

    rate_limit.set_client(BrokenClient())
    allowed, retry_after = rate_limit.reserve("any", 1, 60)
    assert allowed is True
    assert retry_after == 0
