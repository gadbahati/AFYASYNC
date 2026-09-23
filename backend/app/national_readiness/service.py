"""Final national readiness declaration — aggregates prior phase gates.

Hardened: each gate uses the real service signature; failures are isolated.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session


def _safe(fn, *args, **kwargs):
    try:
        return {"ok": True, "data": fn(*args, **kwargs)}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:400]}


def _band_from(gate: dict, fallback: str = "AMBER") -> str:
    if not gate.get("ok"):
        return "RED"
    data = gate.get("data")
    if not isinstance(data, dict):
        return fallback
    if "band" in data:
        return str(data["band"]).upper()
    verdict = str(data.get("verdict") or "").upper()
    if verdict == "ACCEPTANCE_PASS":
        return "GREEN"
    if verdict == "WARMUP":
        return "AMBER"
    if verdict == "ACCEPTANCE_FAIL":
        return "RED"
    if data.get("all_ok") is True:
        return "GREEN"
    if data.get("all_ok") is False:
        return "AMBER"
    if data.get("ready") is True:
        return "GREEN"
    if data.get("ready") is False:
        return "RED"
    if data.get("deploy_blocked") is True:
        return "RED"
    return fallback


def declaration(db: Session) -> dict:
    gates: dict = {}

    try:
        from app.production.service import production_readiness

        gates["production"] = _safe(production_readiness)
    except Exception as exc:
        gates["production"] = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}

    try:
        from app.observability.service import evaluate_slos

        gates["observability"] = _safe(evaluate_slos)
    except Exception as exc:
        gates["observability"] = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}

    try:
        from app.disaster_recovery.service import posture as dr_posture

        gates["disaster_recovery"] = _safe(dr_posture, db)
    except Exception as exc:
        gates["disaster_recovery"] = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}

    try:
        from app.performance.service import evaluate_acceptance

        gates["performance"] = _safe(evaluate_acceptance)
    except Exception as exc:
        gates["performance"] = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}

    try:
        from app.risk_register.service import posture as risk_posture

        gates["risk_register"] = _safe(risk_posture, db)
    except Exception as exc:
        gates["risk_register"] = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}

    try:
        from app.certification.submission_kit import submission_kit

        gates["certification"] = _safe(submission_kit)
    except Exception as exc:
        gates["certification"] = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}

    try:
        from app.pilot_handover.service import pilot_evidence_pack

        gates["pilot_evidence"] = _safe(pilot_evidence_pack, db)
    except Exception as exc:
        gates["pilot_evidence"] = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}

    try:
        from app.reliability.service import readiness_matrix

        gates["reliability"] = _safe(readiness_matrix, db)
    except Exception as exc:
        gates["reliability"] = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}

    try:
        from app.change_control.service import governance_policy

        gates["change_control"] = _safe(governance_policy)
    except Exception as exc:
        gates["change_control"] = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:200]}

    bands = {
        "production": _band_from(gates.get("production") or {}),
        "observability": _band_from(gates.get("observability") or {}),
        "disaster_recovery": _band_from(gates.get("disaster_recovery") or {}),
        "performance": _band_from(gates.get("performance") or {}),
        "risk_register": _band_from(gates.get("risk_register") or {}),
        "reliability": _band_from(gates.get("reliability") or {}),
        "certification": "GREEN" if (gates.get("certification") or {}).get("ok") else "RED",
        "pilot_evidence": "GREEN" if (gates.get("pilot_evidence") or {}).get("ok") else "RED",
        "change_control": "GREEN" if (gates.get("change_control") or {}).get("ok") else "RED",
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
        "Performance acceptance + national readiness declaration",
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
