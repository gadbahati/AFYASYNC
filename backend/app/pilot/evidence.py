"""Combine certification, national readiness, pilot gates into one evidence pack."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.certification.checklist import summarise_checklist
from app.certification.security_posture import security_posture
from app.pilot.checklist import pilot_checklist_template
from app.pilot.migration import migration_readiness


def build_evidence_pack(db: Session, *, facility_id=None) -> dict:
    cert = summarise_checklist()
    posture = security_posture()
    pilot = pilot_checklist_template()
    migration = migration_readiness(db, facility_id=facility_id)

    national = None
    try:
        from app.national_ops.readiness import national_readiness

        national = national_readiness(db)
    except Exception as exc:
        national = {"error": str(exc)[:200]}

    blockers = []
    if posture.get("critical_failed", 0) > 0:
        blockers.append("Security posture has CRITICAL failures")
    if isinstance(national, dict) and national.get("status") == "NOT_READY":
        blockers.append("National readiness NOT_READY")

    return {
        "pack": "AFYASYNC_PILOT_EVIDENCE",
        "phase": 14,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "certification_summary": cert,
        "security_posture": {
            "posture": posture.get("posture"),
            "passed": posture.get("passed"),
            "failed": posture.get("failed"),
            "critical_failed": posture.get("critical_failed"),
        },
        "national_readiness": national,
        "pilot_gates": pilot,
        "migration": migration,
        "go_live_blockers": blockers,
        "go_live_recommendation": "HOLD" if blockers else "READY_FOR_PILOT_REVIEW",
        "developer": "BAHATI GAD WANGWE",
        "disclaimer": "Not a DHA certificate. Evidence for assessors and facility boards only.",
    }
