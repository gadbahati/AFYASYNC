import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status


class AuthRateLimiter:
    """Process-local authentication abuse guard.

    A trusted edge/load-balancer should also enforce distributed limits in a
    multi-instance deployment. Client-supplied forwarding headers are ignored
    here so an attacker cannot rotate them to bypass the worker-local guard.
    """

    def __init__(self, limit: int = 30, window_seconds: int = 60, max_keys: int = 10_000):
        if limit <= 0 or window_seconds <= 0 or max_keys <= 0:
            raise ValueError("rate limiter settings must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    @staticmethod
    def _key(request: Request) -> str:
        host = request.client.host if request.client else "unknown"
        return f"{request.url.path}:{host}"

    def check(self, request: Request) -> None:
        now = time.monotonic()
        key = self._key(request)
        with self._lock:
            cutoff = now - self.window_seconds
            if len(self._events) >= self.max_keys and key not in self._events:
                self._cleanup_locked(cutoff)
            if len(self._events) >= self.max_keys and key not in self._events:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"code": "AUTH_RATE_LIMITED", "message": "Too many authentication attempts. Try again later."},
                    headers={"Retry-After": str(self.window_seconds)},
                )
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - events[0])))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"code": "AUTH_RATE_LIMITED", "message": "Too many authentication attempts. Try again later."},
                    headers={"Retry-After": str(retry_after)},
                )
            events.append(now)

    def _cleanup_locked(self, cutoff: float) -> None:
        stale = []
        for key, events in self._events.items():
            while events and events[0] <= cutoff:
                events.popleft()
            if not events:
                stale.append(key)
        for key in stale:
            self._events.pop(key, None)

    def cleanup(self) -> None:
        with self._lock:
            self._cleanup_locked(time.monotonic() - self.window_seconds)


_auth_rate_limiter = AuthRateLimiter()


def enforce_auth_rate_limit(request: Request) -> None:
    if request.url.path in {"/api/v1/auth/login", "/api/v1/auth/refresh"}:
        _auth_rate_limiter.check(request)
