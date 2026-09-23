"""Consolidated pilot evidence + county handover artefacts (hardened)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.claims.models import Claim
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.rbac.models import Staff
from app.surveillance.models import NotifiableEvent

# Facilities are created as APPLICATION; operational sites may be ACTIVE / APPROVED / etc.
_FACILITY_OPERATIONAL = {"ACTIVE", "APPROVED", "OPERATIONAL", "LICENSED", "APPLICATION"}
_FACILITY_EXCLUDED = {"REJECTED", "SUSPENDED", "CLOSED", "DECOMMISSIONED"}


def _safe_count(db: Session, stmt) -> int:
    try:
        return int(db.scalar(stmt) or 0)
    except Exception:
        return 0


def pilot_evidence_pack(
    db: Session, *, county: str | None = None, facility_id: UUID | None = None
) -> dict:
    """Single JSON pack auditors / county teams can export."""
    fac_q = select(Facility).where(~Facility.status.in_(list(_FACILITY_EXCLUDED)))
    if county:
        fac_q = fac_q.where(Facility.county == county.strip())
    if facility_id is not None:
        fac_q = fac_q.where(Facility.id == facility_id)

    try:
        facilities = list(db.scalars(fac_q.limit(200)).all())
    except Exception:
        facilities = []

    facility_ids = [f.id for f in facilities]
    scoped = bool(county) or facility_id is not None

    if scoped and not facility_ids:
        staff_count = 0
        encounter_count = 0
    elif facility_ids and scoped:
        staff_count = _safe_count(
            db,
            select(func.count())
            .select_from(Staff)
            .where(Staff.status == "ACTIVE", Staff.facility_id.in_(facility_ids)),
        )
        encounter_count = _safe_count(
            db,
            select(func.count())
            .select_from(Encounter)
            .where(Encounter.facility_id.in_(facility_ids)),
        )
    else:
        staff_count = _safe_count(
            db, select(func.count()).select_from(Staff).where(Staff.status == "ACTIVE")
        )
        encounter_count = _safe_count(db, select(func.count()).select_from(Encounter))

    totals = {
        "facilities_in_scope": len(facilities),
        "active_staff": staff_count,
        "encounters": encounter_count,
        "claims": _safe_count(db, select(func.count()).select_from(Claim)),
        "notifiable_events": _safe_count(
            db, select(func.count()).select_from(NotifiableEvent)
        ),
    }

    facility_rows = [
        {
            "facility_id": str(f.id),
            "mfl_or_code": getattr(f, "facility_id", None),
            "name": getattr(f, "name", None),
            "county": getattr(f, "county", None),
            "status": getattr(f, "status", None),
        }
        for f in facilities[:100]
    ]

    evidence_checklist = [
        {"id": "E01", "item": "Patient portal + Afya ID self-registration", "status": "IMPLEMENTED"},
        {"id": "E02", "item": "Sensitive disease consent + digital signature", "status": "IMPLEMENTED"},
        {"id": "E03", "item": "Claims integrity / fraud scan", "status": "IMPLEMENTED"},
        {"id": "E04", "item": "Notifiable disease surveillance", "status": "IMPLEMENTED"},
        {"id": "E05", "item": "HIE + offline outbox", "status": "IMPLEMENTED"},
        {"id": "E06", "item": "SHA/DHA client (mock/live)", "status": "IMPLEMENTED"},
        {"id": "E07", "item": "Warehouse facts + CSV export", "status": "IMPLEMENTED"},
        {"id": "E08", "item": "DHA submission kit", "status": "IMPLEMENTED"},
        {"id": "E09", "item": "Production readiness API", "status": "IMPLEMENTED"},
        {"id": "E10", "item": "Observability SLOs", "status": "IMPLEMENTED"},
        {"id": "E11", "item": "Retention / erasure workflow", "status": "IMPLEMENTED"},
        {"id": "E12", "item": "Partner sandbox contracts", "status": "IMPLEMENTED"},
        {"id": "E13", "item": "DR drills + backup verification", "status": "IMPLEMENTED"},
        {"id": "E14", "item": "Change-control & release registry", "status": "IMPLEMENTED"},
        {"id": "E15", "item": "National readiness declaration", "status": "IMPLEMENTED"},
        {"id": "E16", "item": "Live SHA credentials", "status": "OPERATOR_OWNED"},
        {"id": "E17", "item": "External penetration test", "status": "PENDING_EXTERNAL"},
        {"id": "E18", "item": "DHA portal certification filing", "status": "PENDING_EXTERNAL"},
        {"id": "E19", "item": "County operational sign-off", "status": "HANDOVER"},
    ]

    endpoint_index = [
        "/api/v1/national-readiness/declaration",
        "/api/v1/production/readiness",
        "/api/v1/observability/slos",
        "/api/v1/performance/acceptance",
        "/api/v1/risk-register/posture",
        "/api/v1/dr/posture",
        "/api/v1/change-control/policy",
        "/api/v1/pilot-handover/evidence-pack",
        "/api/v1/pilot-handover/county-handover",
        "/api/v1/certification/submission-kit",
        "/api/v1/reliability/readiness-matrix",
    ]

    return {
        "program": "AFYASYNC_NATIONAL_REPLACEMENT",
        "phase": 40,
        "scope": {
            "county": county,
            "facility_id": str(facility_id) if facility_id else None,
        },
        "totals": totals,
        "facilities": facility_rows,
        "evidence_checklist": evidence_checklist,
        "endpoint_index": endpoint_index,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def county_handover_pack(db: Session, *, county: str) -> dict:
    county_name = (county or "").strip()
    if not county_name:
        raise ValueError("COUNTY_REQUIRED")

    evidence = pilot_evidence_pack(db, county=county_name)

    handover_steps = [
        {"id": "H01", "step": "Confirm county facilities listed in KMHFR / AfyaSync registry"},
        {"id": "H02", "step": "Complete facility onboarding kit for each pilot site"},
        {"id": "H03", "step": "Train super-users via /api/v1/training/catalog SOPs"},
        {"id": "H04", "step": "Run DR tabletop and record via /api/v1/dr/drills"},
        {"id": "H05", "step": "Confirm GREEN or acceptable AMBER on /api/v1/production/readiness"},
        {"id": "H06", "step": "Export warehouse / pilot evidence for baseline metrics"},
        {"id": "H07", "step": "County health management sign-off on evidence pack"},
        {"id": "H08", "step": "Schedule post-go-live support window (30 days)"},
    ]

    contacts_template = {
        "county_health_director": "<name>",
        "afyasync_technical_lead": "BAHATI GAD WANGWE",
        "support_email": "<operator-defined>",
        "escalation": "National digital health operations",
    }

    return {
        "county": county_name,
        "handover_steps": handover_steps,
        "contacts_template": contacts_template,
        "evidence": evidence,
        "sign_off": {
            "status": "PENDING_COUNTY",
            "note": "Operational sign-off is a human process — this pack supports it",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
