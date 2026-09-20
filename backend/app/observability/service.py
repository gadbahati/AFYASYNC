from datetime import datetime, timezone
from threading import Lock


class RuntimeMetrics:
    """Process-local aggregate operational counters; never store request payloads or patient identifiers."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = datetime.now(timezone.utc)
        self._requests = 0
        self._errors = 0
        self._client_errors = 0
        self._server_errors = 0
        self._total_duration_seconds = 0.0
        self._max_duration_seconds = 0.0

    def request(self, error: bool = False, status_code: int | None = None, duration_seconds: float = 0.0) -> None:
        with self._lock:
            self._requests += 1
            if error:
                self._errors += 1
            if status_code is not None and 400 <= status_code < 500:
                self._client_errors += 1
            if status_code is not None and status_code >= 500:
                self._server_errors += 1
            duration = max(float(duration_seconds), 0.0)
            self._total_duration_seconds += duration
            self._max_duration_seconds = max(self._max_duration_seconds, duration)

    def snapshot(self) -> dict:
        with self._lock:
            requests = self._requests
            errors = self._errors
            return {
                "started_at": self._started_at.isoformat(),
                "requests": requests,
                "errors": errors,
                "client_errors": self._client_errors,
                "server_errors": self._server_errors,
                "error_rate": round(errors / requests, 4) if requests else 0.0,
                "average_duration_seconds": round(self._total_duration_seconds / requests, 4) if requests else 0.0,
                "max_duration_seconds": round(self._max_duration_seconds, 4),
            }


runtime_metrics = RuntimeMetrics()
