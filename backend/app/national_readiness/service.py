"""Final national readiness declaration — aggregates prior phase gates."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session


def _safe(fn, *args, **kwargs):
    try:
        return {"ok": True, "data": fn(*args, **kwargs)}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:300]}


def declaration(db: Session) -> dict:
    gates: dict = {}

    # Production
    try:
        from app.production.service import production_readiness

        gates["production"] = _safe(production_readiness, db)
    except Exception as exc:
        gates["production"] = {"ok": False, "error": type(exc).__name__}

    # Observability SLOs
    try:
        from app.observability.service import evaluate_slos

        gates["observability"] = _safe(evaluate_slos, db)
    except Exception as exc:
        gates["observability"] = {"ok": False, "error": type(exc).__name__}

    # DR posture
    try:
        from app.disaster_recovery.service import posture as dr_posture

        gates["disaster_recovery"] = _safe(dr_posture, db)
    except Exception as exc:
        gates["disaster_recovery"] = {"ok": False, "error": type(exc).__name__}

    # Performance acceptance
    try:
        from app.performance.service import evaluate_acceptance

        gates["performance"] = _safe(evaluate_acceptance)
    except Exception as exc:
        gates["performance"] = {"ok": False, "error": type(exc).__name__}

    # Residual risk
    try:
        from app.risk_register.service import posture as risk_posture

        gates["risk_register"] = _safe(risk_posture, db)
    except Exception as exc:
        gates["risk_register"] = {"ok": False, "error": type(exc).__name__}

    # Certification evidence
    try:
        from app.certification.service import submission_kit

        gates["certification"] = _safe(submission_kit, db)
    except Exception as exc:
        gates["certification"] = {"ok": False, "error": type(exc).__name__}

    # Pilot evidence
    try:
        from app.pilot_handover.service import pilot_evidence_pack

        gates["pilot_evidence"] = _safe(pilot_evidence_pack, db)
    except Exception as exc:
        gates["pilot_evidence"] = {"ok": False, "error": type(exc).__name__}

    # Reliability probes
    try:
        from app.reliability.service import get_probes

        gates["reliability"] = _safe(get_probes, db)
    except Exception as exc:
        gates["reliability"] = {"ok": False, "error": type(exc).__name__}

    # Score bands from known shapes
    def _band(key: str) -> str:
        g = gates.get(key) or {}
        if not g.get("ok"):
            return "RED"
        data = g.get("data") or {}
        if isinstance(data, dict):
            if "band" in data:
                return str(data["band"]).upper()
            if data.get("verdict") == "ACCEPTANCE_PASS":
                return "GREEN"
            if data.get("verdict") == "WARMUP":
                return "AMBER"
            if data.get("verdict") == "ACCEPTANCE_FAIL":
                return "RED"
            if data.get("ready") is True:
                return "GREEN"
            if data.get("ready") is False:
                return "RED"
        return "AMBER"

    bands = {
        "production": _band("production"),
        "observability": _band("observability"),
        "disaster_recovery": _band("disaster_recovery"),
        "performance": _band("performance"),
        "risk_register": _band("risk_register"),
        "reliability": _band("reliability"),
    }

    reds = [k for k, v in bands.items() if v == "RED"]
    ambers = [k for k, v in bands.items() if v == "AMBER"]

    if reds:
        overall = "NOT_READY"
        overall_band = "RED"
    elif ambers:
        overall = "CONDITIONAL"
        overall_band = "AMBER"
    else:
        overall = "READY_FOR_PILOT_SCALE"
        overall_band = "GREEN"

    operator_owned = [
        "Live SHA/DHA production credentials",
        "External penetration test report",
        "DHA certification portal filing",
        "County operational sign-off",
        "National-scale k6/Locust evidence in lab",
        "Full restore drill with measured RTO/RPO",
    ]

    capability_summary = [
        "Citizen portal with Afya ID / SHA ID self-registration",
        "Sensitive disease consent with on-screen digital signature",
        "Hospital OS: clinical, claims, inventory, workforce",
        "Claims quality scoring + fraud integrity signals",
        "HIE FHIR-oriented export with consent gates",
        "Offline outbox resilience",
        "Surveillance + quality scorecard + warehouse facts",
        "Production readiness, observability SLOs, DR drills",
        "Change-control + residual risk register",
        "Pilot evidence pack + county handover",
    ]

    return {
        "program": "AFYASYNC_NATIONAL_REPLACEMENT",
        "phase": 40,
        "title": "Final national readiness declaration",
        "overall": overall,
        "overall_band": overall_band,
        "gate_bands": bands,
        "gates": gates,
        "reds": reds,
        "ambers": ambers,
        "capability_summary": capability_summary,
        "operator_owned_remaining": operator_owned,
        "statement": (
            "AfyaSync software gates for a national pilot-scale platform are aggregated here. "
            "A GREEN band means in-platform controls pass; it is not a substitute for MoH/DHA "
            "certification, live SHA credentials, external security testing, or county sign-off."
        ),
        "developer": "BAHATI GAD WANGWE",
        "copyright": "© 2026 AfyaSync. Developed by BAHATI GAD WANGWE. Unauthorised copying prohibited.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
