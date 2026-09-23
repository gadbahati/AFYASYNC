"""County rollout dashboard + consolidated pilot evidence."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ambulance.models import AmbulanceRequest
from app.claims.models import Claim
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.rbac.models import Staff
from app.surveillance.models import NotifiableEvent
from app.telemedicine.models import TeleConsultRequest


def county_rollout_dashboard(db: Session, *, limit_counties: int = 50) -> dict:
    limit_counties = max(1, min(limit_counties, 100))

    facilities = list(
        db.scalars(select(Facility).where(Facility.status == "ACTIVE")).all()
    )

    by_county: dict[str, dict] = defaultdict(
        lambda: {
            "facility_count": 0,
            "staff_count": 0,
            "encounters": 0,
            "claims": 0,
            "notifiable": 0,
            "ambulance": 0,
            "teleconsult": 0,
        }
    )

    for fac in facilities:
        county = (getattr(fac, "county", None) or "UNKNOWN").strip() or "UNKNOWN"
        by_county[county]["facility_count"] += 1

    staff_rows = db.execute(
        select(Facility.county, func.count())
        .select_from(Staff)
        .join(Facility, Facility.id == Staff.facility_id)
        .where(Staff.status == "ACTIVE", Facility.status == "ACTIVE")
        .group_by(Facility.county)
    ).all()
    for county, cnt in staff_rows:
        key = (county or "UNKNOWN").strip() or "UNKNOWN"
        by_county[key]["staff_count"] = int(cnt)

    enc_rows = db.execute(
        select(Facility.county, func.count())
        .select_from(Encounter)
        .join(Facility, Facility.id == Encounter.facility_id)
        .where(Facility.status == "ACTIVE")
        .group_by(Facility.county)
    ).all()
    for county, cnt in enc_rows:
        key = (county or "UNKNOWN").strip() or "UNKNOWN"
        by_county[key]["encounters"] = int(cnt)

    claim_rows = db.execute(
        select(Facility.county, func.count())
        .select_from(Claim)
        .join(Encounter, Encounter.id == Claim.encounter_id)
        .join(Facility, Facility.id == Encounter.facility_id)
        .where(Facility.status == "ACTIVE")
        .group_by(Facility.county)
    ).all()
    for county, cnt in claim_rows:
        key = (county or "UNKNOWN").strip() or "UNKNOWN"
        by_county[key]["claims"] = int(cnt)

    notif_rows = db.execute(
        select(Facility.county, func.count())
        .select_from(NotifiableEvent)
        .join(Facility, Facility.id == NotifiableEvent.facility_id)
        .where(Facility.status == "ACTIVE")
        .group_by(Facility.county)
    ).all()
    for county, cnt in notif_rows:
        key = (county or "UNKNOWN").strip() or "UNKNOWN"
        by_county[key]["notifiable"] = int(cnt)

    amb_rows = db.execute(
        select(Facility.county, func.count())
        .select_from(AmbulanceRequest)
        .join(Facility, Facility.id == AmbulanceRequest.facility_id)
        .where(Facility.status == "ACTIVE")
        .group_by(Facility.county)
    ).all()
    for county, cnt in amb_rows:
        key = (county or "UNKNOWN").strip() or "UNKNOWN"
        by_county[key]["ambulance"] = int(cnt)

    tele_rows = db.execute(
        select(Facility.county, func.count())
        .select_from(TeleConsultRequest)
        .join(Facility, Facility.id == TeleConsultRequest.facility_id)
        .where(Facility.status == "ACTIVE")
        .group_by(Facility.county)
    ).all()
    for county, cnt in tele_rows:
        key = (county or "UNKNOWN").strip() or "UNKNOWN"
        by_county[key]["teleconsult"] = int(cnt)

    counties = []
    for name, data in by_county.items():
        score = 0.0
        score += min(data["facility_count"], 10) * 4
        score += 15 if data["staff_count"] > 0 else 0
        score += 15 if data["encounters"] > 0 else 0
        score += 10 if data["claims"] > 0 else 0
        score += 10 if data["notifiable"] > 0 else 0
        score += 5 if data["ambulance"] > 0 else 0
        score += 5 if data["teleconsult"] > 0 else 0
        score = round(min(100.0, score), 1)
        band = "GREEN" if score >= 70 else ("AMBER" if score >= 40 else "RED")
        counties.append(
            {
                "county": name,
                "facility_count": data["facility_count"],
                "staff_count": data["staff_count"],
                "encounters": data["encounters"],
                "claims": data["claims"],
                "notifiable_events": data["notifiable"],
                "ambulance_requests": data["ambulance"],
                "teleconsult_requests": data["teleconsult"],
                "maturity_score": score,
                "band": band,
            }
        )

    counties.sort(key=lambda c: (-c["maturity_score"], c["county"]))
    counties = counties[:limit_counties]

    bands = {"GREEN": 0, "AMBER": 0, "RED": 0}
    for c in counties:
        bands[c["band"]] = bands.get(c["band"], 0) + 1

    return {
        "county_count": len(counties),
        "bands": bands,
        "counties": counties,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def pilot_evidence_pack(db: Session, *, facility_id: UUID | None = None) -> dict:
    total_facilities = db.scalar(
        select(func.count()).select_from(Facility).where(Facility.status == "ACTIVE")
    ) or 0
    total_staff = db.scalar(
        select(func.count()).select_from(Staff).where(Staff.status == "ACTIVE")
    ) or 0
    total_encounters = db.scalar(select(func.count()).select_from(Encounter)) or 0
    total_claims = db.scalar(select(func.count()).select_from(Claim)) or 0
    total_notif = db.scalar(select(func.count()).select_from(NotifiableEvent)) or 0

    facility_slice = None
    if facility_id is not None:
        fac = db.get(Facility, facility_id)
        if fac is None:
            raise ValueError("FACILITY_NOT_FOUND")
        facility_slice = {
            "facility_id": str(facility_id),
            "name": getattr(fac, "name", None),
            "county": getattr(fac, "county", None),
            "status": getattr(fac, "status", None),
            "staff": int(
                db.scalar(
                    select(func.count()).select_from(Staff).where(
                        Staff.facility_id == facility_id, Staff.status == "ACTIVE"
                    )
                )
                or 0
            ),
            "encounters": int(
                db.scalar(
                    select(func.count()).select_from(Encounter).where(
                        Encounter.facility_id == facility_id
                    )
                )
                or 0
            ),
            "claims": int(
                db.scalar(
                    select(func.count())
                    .select_from(Claim)
                    .join(Encounter, Encounter.id == Claim.encounter_id)
                    .where(Encounter.facility_id == facility_id)
                )
                or 0
            ),
        }

    evidence_checklist = [
        {"id": "IDENTITY_PORTAL", "label": "Citizen/patient portal with Afya ID", "status": "IMPLEMENTED"},
        {"id": "CONSENT_SENSITIVE", "label": "Sensitive disease consent + signature", "status": "IMPLEMENTED"},
        {"id": "CLAIMS_INTEGRITY", "label": "Fraud-integrity facility scan", "status": "IMPLEMENTED"},
        {"id": "SURVEILLANCE", "label": "Notifiable event reporting", "status": "IMPLEMENTED"},
        {"id": "HIE_OFFLINE", "label": "HIE + offline outbox", "status": "IMPLEMENTED"},
        {"id": "SHA_CLIENT", "label": "SHA/DHA client (mock/live modes)", "status": "IMPLEMENTED"},
        {"id": "ONBOARDING_KIT", "label": "Facility onboarding kit", "status": "IMPLEMENTED"},
        {"id": "TRAINING_SOPS", "label": "Training SOP API", "status": "IMPLEMENTED"},
        {"id": "RELIABILITY", "label": "Reliability readiness matrix", "status": "IMPLEMENTED"},
        {"id": "WAREHOUSE", "label": "National warehouse facts + CSV export", "status": "IMPLEMENTED"},
        {"id": "DHA_SUBMISSION_KIT", "label": "Certification submission kit", "status": "IMPLEMENTED"},
        {"id": "LIVE_SHA_CREDS", "label": "Production SHA tokens", "status": "OPERATOR_OWNED"},
        {"id": "EXTERNAL_PENTEST", "label": "Independent penetration test", "status": "PENDING_EXTERNAL"},
        {"id": "DHA_CERT", "label": "DHA certification submission", "status": "PENDING_EXTERNAL"},
    ]

    return {
        "program": "AFYASYNC_NATIONAL_REPLACEMENT",
        "phase": 30,
        "national_totals": {
            "active_facilities": int(total_facilities),
            "active_staff": int(total_staff),
            "encounters": int(total_encounters),
            "claims": int(total_claims),
            "notifiable_events": int(total_notif),
        },
        "facility_slice": facility_slice,
        "evidence_checklist": evidence_checklist,
        "related_endpoints": [
            "/api/v1/pilot/evidence-pack",
            "/api/v1/onboarding/facility-kit",
            "/api/v1/reliability/readiness-matrix",
            "/api/v1/fraud-integrity/facility-scan",
            "/api/v1/certification/evidence",
            "/api/v1/certification/submission-kit",
            "/api/v1/rollout/county-dashboard",
            "/api/v1/warehouse/facts",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
