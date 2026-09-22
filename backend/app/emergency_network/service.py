"""Emergency load board + referral destination suggestions — hardened."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.emergency.models import EmergencyVisit
from app.facilities.models import Facility, FacilityRegistryRecord
from app.referrals.models import Referral, Transfer

OPEN_ER_STATUSES = {"WAITING", "TRIAGED", "IN_CARE", "ACTIVE", "OPEN", "BEING_SEEN"}
OPEN_REF_STATUSES = {"CREATED", "SENT", "ACCEPTED", "IN_TRANSIT", "PENDING"}


def _iso(dt) -> str | None:
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def emergency_board(
    db: Session,
    *,
    facility_id: UUID | None = None,
    county: str | None = None,
    limit: int = 100,
) -> dict:
    limit = max(1, min(limit, 200))
    q = select(EmergencyVisit, Facility).join(Facility, Facility.id == EmergencyVisit.facility_id)
    if facility_id:
        q = q.where(EmergencyVisit.facility_id == facility_id)
    if county:
        q = q.where(Facility.county == county.strip())
    q = q.where(EmergencyVisit.status.in_(list(OPEN_ER_STATUSES))).order_by(
        EmergencyVisit.arrived_at.asc()
    )

    visits = []
    by_triage = defaultdict(int)
    for visit, fac in db.execute(q.limit(limit)).all():
        by_triage[str(visit.triage_level or "UNKNOWN")] += 1
        visits.append(
            {
                "visit_id": str(visit.id),
                "visit_number": getattr(visit, "visit_number", None),
                "facility_id": str(fac.id),
                "facility_name": getattr(fac, "name", None),
                "county": getattr(fac, "county", None),
                "triage_level": visit.triage_level,
                "status": visit.status,
                "arrived_at": _iso(getattr(visit, "arrived_at", None)),
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "open_count": len(visits),
        "by_triage": dict(by_triage),
        "visits": visits,
        "developer": "BAHATI GAD WANGWE",
    }


def facility_emergency_load(db: Session, *, facility_id: UUID) -> dict:
    open_count = db.scalar(
        select(func.count()).select_from(EmergencyVisit).where(
            EmergencyVisit.facility_id == facility_id,
            EmergencyVisit.status.in_(list(OPEN_ER_STATUSES)),
        )
    ) or 0
    day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    last_24h = db.scalar(
        select(func.count()).select_from(EmergencyVisit).where(
            EmergencyVisit.facility_id == facility_id,
            EmergencyVisit.arrived_at >= day_ago,
        )
    ) or 0
    by_triage = {
        str(t): int(c)
        for t, c in db.execute(
            select(EmergencyVisit.triage_level, func.count())
            .where(
                EmergencyVisit.facility_id == facility_id,
                EmergencyVisit.status.in_(list(OPEN_ER_STATUSES)),
            )
            .group_by(EmergencyVisit.triage_level)
        ).all()
    }
    if open_count >= 30:
        band = "HIGH"
    elif open_count >= 10:
        band = "MODERATE"
    else:
        band = "LOW"
    return {
        "facility_id": str(facility_id),
        "open_emergency_visits": int(open_count),
        "visits_last_24h": int(last_24h),
        "by_triage": by_triage,
        "load_band": band,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def referral_destinations(
    db: Session,
    *,
    source_facility_id: UUID,
    preferred_county: str | None = None,
    limit: int = 20,
) -> dict:
    limit = max(1, min(limit, 50))
    source = db.get(Facility, source_facility_id)
    if source is None:
        raise ValueError("FACILITY_NOT_FOUND")

    county = preferred_county or getattr(source, "county", None)
    q = (
        select(Facility, FacilityRegistryRecord)
        .outerjoin(FacilityRegistryRecord, FacilityRegistryRecord.facility_id == Facility.id)
        .where(Facility.status == "ACTIVE", Facility.id != source_facility_id)
    )
    if county:
        q = q.where(Facility.county == county)

    candidates = []
    for fac, reg in db.execute(q.limit(200)).all():
        open_er = db.scalar(
            select(func.count()).select_from(EmergencyVisit).where(
                EmergencyVisit.facility_id == fac.id,
                EmergencyVisit.status.in_(list(OPEN_ER_STATUSES)),
            )
        ) or 0
        keph = (reg.keph_level if reg else None) or getattr(fac, "facility_type", None) or "UNKNOWN"
        candidates.append(
            {
                "facility_id": str(fac.id),
                "facility_name": getattr(fac, "name", None),
                "county": getattr(fac, "county", None),
                "keph_or_type": keph,
                "open_emergency_load": int(open_er),
            }
        )

    candidates.sort(key=lambda x: (x["open_emergency_load"], x["facility_name"] or ""))

    open_refs = db.scalar(
        select(func.count()).select_from(Referral).where(
            Referral.source_facility_id == source_facility_id,
            Referral.status.in_(list(OPEN_REF_STATUSES)),
        )
    ) or 0

    return {
        "source_facility_id": str(source_facility_id),
        "source_name": getattr(source, "name", None),
        "county_filter": county,
        "open_outbound_referrals": int(open_refs),
        "suggestions": candidates[:limit],
        "note": "Advisory routing — clinical decision and receiving facility acceptance required",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def network_overview(db: Session, *, days: int = 7) -> dict:
    days = max(1, min(days, 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    open_er = db.scalar(
        select(func.count()).select_from(EmergencyVisit).where(
            EmergencyVisit.status.in_(list(OPEN_ER_STATUSES))
        )
    ) or 0
    er_window = db.scalar(
        select(func.count()).select_from(EmergencyVisit).where(EmergencyVisit.arrived_at >= since)
    ) or 0
    open_ref = db.scalar(
        select(func.count()).select_from(Referral).where(
            Referral.status.in_(list(OPEN_REF_STATUSES))
        )
    ) or 0
    open_xfer = db.scalar(
        select(func.count()).select_from(Transfer).where(
            Transfer.status.in_(["REQUESTED", "IN_TRANSIT", "ACCEPTED"])
        )
    ) or 0
    return {
        "window_days": days,
        "open_emergency_visits": int(open_er),
        "emergency_visits_in_window": int(er_window),
        "open_referrals": int(open_ref),
        "open_transfers": int(open_xfer),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
