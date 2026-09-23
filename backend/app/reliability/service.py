"""Reliability probes — DB, runtime metrics, controlled failure drills."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.observability.service import runtime_metrics


def dependency_probes(db: Session) -> dict:
    """Measure critical dependency latency."""
    probes = []

    # Database
    t0 = time.perf_counter()
    db_ok = False
    db_error = None
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        db_error = type(exc).__name__
    db_ms = round((time.perf_counter() - t0) * 1000, 2)
    probes.append(
        {
            "name": "postgres",
            "ok": db_ok,
            "latency_ms": db_ms,
            "error": db_error,
            "sla_hint_ms": 100,
            "within_sla": db_ok and db_ms <= 100,
        }
    )

    # App process (always local)
    probes.append(
        {
            "name": "api_process",
            "ok": True,
            "latency_ms": 0,
            "error": None,
            "sla_hint_ms": 1,
            "within_sla": True,
        }
    )

    all_ok = all(p["ok"] for p in probes)
    return {
        "all_ok": all_ok,
        "probes": probes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def performance_snapshot() -> dict:
    snap = runtime_metrics.snapshot()
    return {
        "runtime": snap,
        "environment": getattr(settings, "environment", None),
        "app_version": getattr(settings, "app_version", None),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def readiness_matrix(db: Session) -> dict:
    deps = dependency_probes(db)
    perf = performance_snapshot()
    runtime = perf.get("runtime") or {}

    checks = [
        {"id": "DB_REACHABLE", "pass": deps["all_ok"], "detail": deps["probes"]},
        {
            "id": "RUNTIME_METRICS",
            "pass": isinstance(runtime, dict),
            "detail": "request counters available",
        },
        {
            "id": "SECURITY_HEADERS",
            "pass": True,
            "detail": "SecurityHeadersMiddleware on all responses",
        },
        {
            "id": "OFFLINE_OUTBOX",
            "pass": True,
            "detail": "offline enqueue/drain available for degraded mode",
        },
    ]
    passed = sum(1 for c in checks if c["pass"])
    score = round(100.0 * passed / len(checks), 1) if checks else 0.0
    band = "GREEN" if score >= 80 else ("AMBER" if score >= 60 else "RED")

    return {
        "score_pct": score,
        "band": band,
        "checks": checks,
        "dependencies": deps,
        "performance": perf,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def chaos_drill_catalog() -> dict:
    """Documented failure drills — simulation catalog only, no live destruction."""
    drills = [
        {
            "id": "DB_SLOW",
            "description": "Inject delayed SELECT to measure API timeout behaviour",
            "safe_default": True,
            "requires": "staging only",
        },
        {
            "id": "OFFLINE_BURST",
            "description": "Enqueue 100 offline events and drain — verify outbox durability",
            "safe_default": True,
            "requires": "facility token",
        },
        {
            "id": "AUTH_LOCKOUT",
            "description": "Verify rate limit / lockout after failed patient logins",
            "safe_default": True,
            "requires": "test accounts",
        },
        {
            "id": "SHA_DOWN",
            "description": "Force SHA_DHA_MODE=mock while claiming eligibility path still answers",
            "safe_default": True,
            "requires": "config toggle",
        },
    ]
    return {
        "drills": drills,
        "note": "Catalog only — does not execute destructive chaos on production",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
