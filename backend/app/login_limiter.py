"""登录失败限流（Redis 版本）。

规则与旧实现完全一致：
- 任意 5 分钟内失败 5 次 → 锁定 15 分钟
- 登录成功后清除该来源的失败记录与锁定

与旧实现的差异只在存储：
- 旧：进程内 dict，多 worker 各算各的，进程重启即清零
- 新：Redis 共享状态，多 worker / 多实例 / 重启后都连续

具体实现见 `app/rate_limit.py`。
"""

from app import rate_limit

MAX_FAILURES = 5
WINDOW_SECONDS = 5 * 60
LOCK_SECONDS = 15 * 60


def _fail_key(client_ip: str) -> str:
    return f"login:fail:{client_ip}"


def _lock_key(client_ip: str) -> str:
    return f"login:lock:{client_ip}"


def is_login_blocked(client_ip: str) -> bool:
    """检查某个来源是否处于登录限制期。"""

    return rate_limit.is_locked(_lock_key(client_ip))


def record_login_failure(client_ip: str) -> None:
    """记录一次登录失败，达到阈值后锁定该来源。"""

    count = rate_limit.record_event(_fail_key(client_ip), WINDOW_SECONDS)
    if count >= MAX_FAILURES:
        rate_limit.set_lock(_lock_key(client_ip), LOCK_SECONDS)
        # 锁定后清掉失败计数，解锁后重新从 0 开始
        rate_limit.delete(_fail_key(client_ip))


def clear_login_failures(client_ip: str) -> None:
    """登录成功后，清除该来源的失败记录与锁定。"""

    rate_limit.delete(_fail_key(client_ip), _lock_key(client_ip))


def cleanup_expired_records() -> None:
    """旧实现依赖定期手动清理；Redis 版由 TTL 自动过期。

    保留空实现，兼容 main.py 里已有的调用点，避免为了这次改造
    去动请求主流程。
    """

    return None


def reset_state() -> None:
    """测试用：清空所有登录限流状态。"""

    rate_limit.clear_namespace("login:")
