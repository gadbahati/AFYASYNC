"""Process-local metrics + SLO evaluation (National Phase 32).

Never stores request payloads or patient identifiers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock


class RuntimeMetrics:
    """Process-local aggregate operational counters."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._started_at = datetime.now(timezone.utc)
        self._requests = 0
        self._errors = 0
        self._client_errors = 0
        self._server_errors = 0
        self._total_duration_seconds = 0.0
        self._max_duration_seconds = 0.0
        self._timed_requests = 0

    def request(
        self,
        error: bool = False,
        status_code: int | None = None,
        duration_seconds: float = 0.0,
    ) -> None:
        with self._lock:
            self._requests += 1
            if error:
                self._errors += 1
            if status_code is not None and 400 <= status_code < 500:
                self._client_errors += 1
            if status_code is not None and status_code >= 500:
                self._server_errors += 1
            duration = max(float(duration_seconds), 0.0)
            if duration > 0:
                self._timed_requests += 1
                self._total_duration_seconds += duration
                self._max_duration_seconds = max(self._max_duration_seconds, duration)

    def snapshot(self) -> dict:
        with self._lock:
            requests = self._requests
            errors = self._errors
            timed = self._timed_requests
            return {
                "started_at": self._started_at.isoformat(),
                "requests": requests,
                "errors": errors,
                "client_errors": self._client_errors,
                "server_errors": self._server_errors,
                "error_rate": round(errors / requests, 4) if requests else 0.0,
                "server_error_rate": round(self._server_errors / requests, 4) if requests else 0.0,
                "timed_requests": timed,
                "average_duration_seconds": round(self._total_duration_seconds / timed, 4)
                if timed
                else 0.0,
                "max_duration_seconds": round(self._max_duration_seconds, 4),
            }


runtime_metrics = RuntimeMetrics()

# Target SLOs for the API process (operator-tunable via code for now)
SLO_DEFINITIONS = [
    {
        "id": "SLO-AVAILABILITY",
        "name": "Request success (non-5xx)",
        "target": 0.995,
        "metric": "availability",
        "description": "Share of requests that are not server errors",
    },
    {
        "id": "SLO-ERROR-RATE",
        "name": "Server error rate",
        "target_max": 0.005,
        "metric": "server_error_rate",
        "description": "5xx rate should stay below 0.5%",
    },
    {
        "id": "SLO-LATENCY-AVG",
        "name": "Average latency",
        "target_max_seconds": 2.0,
        "metric": "average_duration_seconds",
        "description": "Mean request duration under 2s when timing is recorded",
    },
]


def evaluate_slos() -> dict:
    snap = runtime_metrics.snapshot()
    requests = int(snap.get("requests") or 0)
    server_errors = int(snap.get("server_errors") or 0)
    availability = (1.0 - (server_errors / requests)) if requests else 1.0
    server_error_rate = float(snap.get("server_error_rate") or 0.0)
    avg_latency = float(snap.get("average_duration_seconds") or 0.0)
    timed = int(snap.get("timed_requests") or 0)

    results = []
    for slo in SLO_DEFINITIONS:
        sid = slo["id"]
        if sid == "SLO-AVAILABILITY":
            target = float(slo["target"])
            ok = availability >= target if requests >= 20 else True  # warm-up grace
            results.append(
                {
                    "id": sid,
                    "name": slo["name"],
                    "ok": ok,
                    "observed": round(availability, 4),
                    "target": target,
                    "sample_requests": requests,
                    "warmup": requests < 20,
                }
            )
        elif sid == "SLO-ERROR-RATE":
            target_max = float(slo["target_max"])
            ok = server_error_rate <= target_max if requests >= 20 else True
            results.append(
                {
                    "id": sid,
                    "name": slo["name"],
                    "ok": ok,
                    "observed": server_error_rate,
                    "target_max": target_max,
                    "sample_requests": requests,
                    "warmup": requests < 20,
                }
            )
        elif sid == "SLO-LATENCY-AVG":
            target_max = float(slo["target_max_seconds"])
            # Only evaluate when we have timed samples
            if timed < 20:
                ok = True
                warmup = True
            else:
                ok = avg_latency <= target_max
                warmup = False
            results.append(
                {
                    "id": sid,
                    "name": slo["name"],
                    "ok": ok,
                    "observed": avg_latency,
                    "target_max_seconds": target_max,
                    "timed_requests": timed,
                    "warmup": warmup,
                }
            )

    all_ok = all(r["ok"] for r in results)
    return {
        "slos": results,
        "all_ok": all_ok,
        "band": "GREEN" if all_ok else "AMBER",
        "runtime": snap,
        "note": "Process-local SLOs — not a multi-instance Prometheus/Grafana stack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def tracing_hooks() -> dict:
    """Document how request correlation works in AfyaSync."""
    return {
        "request_id": {
            "header_in": "X-Request-ID",
            "header_out": "X-Request-ID",
            "behavior": "Accepted if safe charset; otherwise generated UUID",
            "middleware": "SecurityHeadersMiddleware",
        },
        "privacy": "Paths logged via privacy_safe_path — no PHI in logs",
        "metrics": {
            "module": "app.observability.service.runtime_metrics",
            "recorded": ["requests", "errors", "client_errors", "server_errors", "duration"],
        },
        "external_apm": "Optional: attach OpenTelemetry exporter later without changing business APIs",
        "developer": "BAHATI GAD WANGWE",
    }
