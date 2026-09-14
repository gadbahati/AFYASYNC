from datetime import datetime, timezone
from threading import Lock


class RuntimeMetrics:
    """Small process-local operational counters; do not store patient identifiers."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = datetime.now(timezone.utc)
        self._requests = 0
        self._errors = 0

    def request(self, error: bool = False) -> None:
        with self._lock:
            self._requests += 1
            if error:
                self._errors += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {"started_at": self._started_at.isoformat(), "requests": self._requests, "errors": self._errors}


runtime_metrics = RuntimeMetrics()
