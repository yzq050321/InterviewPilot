
import time
from collections import deque
from threading import Lock


MAX_FAILURES = 5
WINDOW_SECONDS = 5 * 60
LOCK_SECONDS = 15 * 60

_failed_attempts: dict[str, deque[float]] = {}
_locked_until: dict[str, float] = {}
_lock = Lock()


def is_login_blocked(client_ip: str) -> bool:
    """检查某个来源是否处于登录限制期。"""

    now = time.monotonic()

    with _lock:
        locked_until = _locked_until.get(client_ip, 0)

        if locked_until > now:
            return True

        if locked_until:
            _locked_until.pop(client_ip, None)

        return False


def record_login_failure(client_ip: str) -> None:
    """记录一次登录失败，超过阈值后暂时限制登录。"""

    now = time.monotonic()

    with _lock:
        attempts = _failed_attempts.setdefault(
            client_ip,
            deque()
        )

        while attempts and now - attempts[0] > WINDOW_SECONDS:
            attempts.popleft()

        attempts.append(now)

        if len(attempts) >= MAX_FAILURES:
            _locked_until[client_ip] = now + LOCK_SECONDS
            _failed_attempts.pop(client_ip, None)


def clear_login_failures(client_ip: str) -> None:
    """登录成功后，清除该来源的失败记录。"""

    with _lock:
        _failed_attempts.pop(client_ip, None)
        _locked_until.pop(client_ip, None)
        
        

def cleanup_expired_records() -> None:
    """清理已经过期的登录失败记录和锁定记录。"""

    now = time.monotonic()

    with _lock:
        # 清理已过期的锁定记录
        expired_ips = [
            ip
            for ip, locked_until in _locked_until.items()
            if locked_until <= now
        ]

        for ip in expired_ips:
            _locked_until.pop(ip, None)

        # 清理超过统计窗口的失败记录
        for ip, attempts in list(_failed_attempts.items()):
            while attempts and now - attempts[0] > WINDOW_SECONDS:
                attempts.popleft()

            if not attempts:
                _failed_attempts.pop(ip, None)