"""Performance acceptance targets + evaluation against runtime metrics."""

from __future__ import annotations

from datetime import datetime, timezone

from app.observability.service import runtime_metrics

# National-scale acceptance targets (guidance for pilot → production)
ACCEPTANCE_TARGETS = [
    {
        "id": "PERF-LAT-AVG",
        "name": "Average API latency",
        "metric": "average_duration_seconds",
        "target_max": 1.5,
        "unit": "seconds",
        "description": "Mean request duration under 1.5s under pilot load",
    },
    {
        "id": "PERF-LAT-MAX",
        "name": "Max observed latency",
        "metric": "max_duration_seconds",
        "target_max": 5.0,
        "unit": "seconds",
        "description": "No single request above 5s in acceptance window",
    },
    {
        "id": "PERF-ERR-5XX",
        "name": "Server error rate",
        "metric": "server_error_rate",
        "target_max": 0.01,
        "unit": "ratio",
        "description": "5xx rate below 1% during load acceptance",
    },
    {
        "id": "PERF-AVAIL",
        "name": "Availability",
        "metric": "availability",
        "target_min": 0.99,
        "unit": "ratio",
        "description": "At least 99% non-5xx responses",
    },
]

LOAD_SCENARIOS = [
    {
        "id": "LS-SMOKE",
        "name": "Smoke",
        "concurrent_users": 10,
        "duration_minutes": 5,
        "focus": ["/health", "/ready", "/api/v1/observability/runtime"],
    },
    {
        "id": "LS-PILOT",
        "name": "Pilot facility day",
        "concurrent_users": 50,
        "duration_minutes": 30,
        "focus": ["encounters", "claims preflight", "portal booking"],
    },
    {
        "id": "LS-COUNTY",
        "name": "County peak",
        "concurrent_users": 200,
        "duration_minutes": 60,
        "focus": ["warehouse facts", "quality scorecard", "rollout dashboard"],
    },
    {
        "id": "LS-NATIONAL",
        "name": "National acceptance (lab)",
        "concurrent_users": 1000,
        "duration_minutes": 120,
        "focus": ["mixed clinical + claims + HIE"],
        "note": "Requires dedicated load lab / k6 or Locust — not executed inside API process",
    },
]


def performance_catalogue() -> dict:
    return {
        "targets": ACCEPTANCE_TARGETS,
        "scenarios": LOAD_SCENARIOS,
        "tools_recommended": ["k6", "Locust", "vegeta"],
        "note": "API evaluates live process metrics; external load tools generate the traffic",
        "developer": "BAHATI GAD WANGWE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def evaluate_acceptance() -> dict:
    snap = runtime_metrics.snapshot()
    requests = int(snap.get("requests") or 0)
    server_errors = int(snap.get("server_errors") or 0)
    availability = (1.0 - (server_errors / requests)) if requests else 1.0
    server_error_rate = float(snap.get("server_error_rate") or 0.0)
    avg_lat = float(snap.get("average_duration_seconds") or 0.0)
    max_lat = float(snap.get("max_duration_seconds") or 0.0)
    timed = int(snap.get("timed_requests") or 0)

    warmup = requests < 50 or timed < 20

    results = []
    for t in ACCEPTANCE_TARGETS:
        tid = t["id"]
        if tid == "PERF-LAT-AVG":
            observed = avg_lat
            ok = True if warmup else observed <= float(t["target_max"])
            results.append(
                {
                    "id": tid,
                    "name": t["name"],
                    "ok": ok,
                    "observed": observed,
                    "target_max": t["target_max"],
                    "warmup": warmup,
                }
            )
        elif tid == "PERF-LAT-MAX":
            observed = max_lat
            ok = True if warmup else observed <= float(t["target_max"])
            results.append(
                {
                    "id": tid,
                    "name": t["name"],
                    "ok": ok,
                    "observed": observed,
                    "target_max": t["target_max"],
                    "warmup": warmup,
                }
            )
        elif tid == "PERF-ERR-5XX":
            observed = server_error_rate
            ok = True if warmup else observed <= float(t["target_max"])
            results.append(
                {
                    "id": tid,
                    "name": t["name"],
                    "ok": ok,
                    "observed": observed,
                    "target_max": t["target_max"],
                    "warmup": warmup,
                }
            )
        elif tid == "PERF-AVAIL":
            observed = round(availability, 4)
            ok = True if warmup else observed >= float(t["target_min"])
            results.append(
                {
                    "id": tid,
                    "name": t["name"],
                    "ok": ok,
                    "observed": observed,
                    "target_min": t["target_min"],
                    "warmup": warmup,
                }
            )

    all_ok = all(r["ok"] for r in results)
    if warmup:
        band = "AMBER"
        verdict = "WARMUP — generate load then re-check"
    elif all_ok:
        band = "GREEN"
        verdict = "ACCEPTANCE_PASS"
    else:
        band = "RED"
        verdict = "ACCEPTANCE_FAIL"

    return {
        "verdict": verdict,
        "band": band,
        "results": results,
        "runtime": snap,
        "sample_requests": requests,
        "timed_requests": timed,
        "scenarios": LOAD_SCENARIOS,
        "note": "Process-local acceptance — run k6/Locust against staging for national-scale proof",
        "developer": "BAHATI GAD WANGWE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
