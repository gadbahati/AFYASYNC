import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status


class AuthRateLimiter:
    """Process-local abuse guard for authentication endpoints.

    The edge/load-balancer must still provide distributed rate limiting in multi-instance
    production. This guard protects each API worker and is deliberately fail-closed only
    for the configured authentication routes.
    """

    def __init__(self, limit: int = 30, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    @staticmethod
    def _key(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
        host = forwarded or (request.client.host if request.client else "unknown")
        return f"{request.url.path}:{host}"

    def check(self, request: Request) -> None:
        now = time.monotonic()
        key = self._key(request)
        with self._lock:
            events = self._events[key]
            cutoff = now - self.window_seconds
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

    def cleanup(self) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            stale = []
            for key, events in self._events.items():
                while events and events[0] <= cutoff:
                    events.popleft()
                if not events:
                    stale.append(key)
            for key in stale:
                self._events.pop(key, None)


_auth_rate_limiter = AuthRateLimiter()


def enforce_auth_rate_limit(request: Request) -> None:
    if request.url.path in {"/api/v1/auth/login", "/api/v1/auth/refresh"}:
        _auth_rate_limiter.check(request)
