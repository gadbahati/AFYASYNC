"""Aggregate care-gap intelligence by county — no patient identifiers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment  # noqa: F401 — capacity context
from app.audit.service import record_audit
from app.billing.models import Invoice
from app.care_gap.schemas import CareGapOverview, CareGapSignal, CountyCareGap
from app.claims.models import Claim
from app.emergency.models import EmergencyVisit
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.pharmacy.models import InventoryItem
from app.portal.messaging_models import AppointmentRequest
from app.referrals.models import Referral
from app.treat_abroad.models import OverseasTreatmentCase
from app.wards.models import Bed, Ward

_ACTIVE_EMERGENCY = ("WAITING", "TRIAGED", "IN_TREATMENT")
_REJECTED_CLAIM = ("REJECTED", "DENIED")
_OPEN_OTA = (
    "DRAFT",
    "SUBMITTED",
    "UNDER_REVIEW",
    "APPROVED",
    "TRAVEL_ARRANGED",
    "TREATMENT_IN_PROGRESS",
    "RETURNED",
)


def _severity(score_part: int) -> str:
    if score_part >= 30:
        return "CRITICAL"
    if score_part >= 20:
        return "HIGH"
    if score_part >= 10:
        return "MEDIUM"
    return "LOW"


def _county_label(raw: str | None) -> str:
    name = (raw or "").strip()
    return name if name else "UNASSIGNED"


def _score_county(
    *,
    facility_count: int,
    open_encounters: int,
    referral_out: int,
    treat_abroad_open: int,
    pending_appts: int,
    rejection_rate: float,
    low_stock: int,
    emergency_waiting: int,
    occupancy_pct: float | None,
) -> tuple[int, list[CareGapSignal]]:
    signals: list[CareGapSignal] = []
    score = 0

    if facility_count == 0:
        return 0, [
            CareGapSignal(
                code="NO_FACILITIES",
                severity="LOW",
                title="No active facilities",
                detail="County has no ACTIVE facilities in AfyaSync",
                metric_value=0,
            )
        ]

    # Encounter pressure (relative per facility)
    enc_per_fac = open_encounters / max(facility_count, 1)
    if enc_per_fac >= 40:
        part = 25
        score += part
        signals.append(
            CareGapSignal(
                code="HIGH_OPEN_ENCOUNTERS",
                severity=_severity(part),
                title="High open encounter load",
                detail=f"~{enc_per_fac:.0f} open encounters per facility",
                metric_value=open_encounters,
            )
        )
    elif enc_per_fac >= 20:
        part = 12
        score += part
        signals.append(
            CareGapSignal(
                code="ELEVATED_OPEN_ENCOUNTERS",
                severity=_severity(part),
                title="Elevated open encounters",
                detail=f"~{enc_per_fac:.0f} open encounters per facility",
                metric_value=open_encounters,
            )
        )

    if referral_out >= 50:
        part = 20
        score += part
        signals.append(
            CareGapSignal(
                code="HIGH_REFERRAL_OUTFLOW",
                severity=_severity(part),
                title="High referral outflow",
                detail="Many patients referred out of county facilities in window",
                metric_value=referral_out,
            )
        )
    elif referral_out >= 15:
        part = 10
        score += part
        signals.append(
            CareGapSignal(
                code="MODERATE_REFERRAL_OUTFLOW",
                severity=_severity(part),
                title="Moderate referral outflow",
                detail="Elevated outbound referrals in window",
                metric_value=referral_out,
            )
        )

    if treat_abroad_open >= 5:
        part = 15
        score += part
        signals.append(
            CareGapSignal(
                code="TREAT_ABROAD_BACKLOG",
                severity=_severity(part),
                title="Treat Abroad open cases",
                detail="Open overseas treatment cases need local capacity planning",
                metric_value=treat_abroad_open,
            )
        )
    elif treat_abroad_open >= 1:
        part = 5
        score += part
        signals.append(
            CareGapSignal(
                code="TREAT_ABROAD_OPEN",
                severity="LOW",
                title="Treat Abroad activity",
                detail="At least one open overseas case",
                metric_value=treat_abroad_open,
            )
        )

    if pending_appts >= 30:
        part = 15
        score += part
        signals.append(
            CareGapSignal(
                code="APPOINTMENT_BACKLOG",
                severity=_severity(part),
                title="Appointment request backlog",
                detail="Patient appointment requests waiting on facilities",
                metric_value=pending_appts,
            )
        )
    elif pending_appts >= 10:
        part = 8
        score += part
        signals.append(
            CareGapSignal(
                code="APPOINTMENT_QUEUE",
                severity=_severity(part),
                title="Pending appointment requests",
                detail="Growing patient request queue",
                metric_value=pending_appts,
            )
        )

    if rejection_rate >= 25:
        part = 20
        score += part
        signals.append(
            CareGapSignal(
                code="HIGH_CLAIM_REJECTION",
                severity=_severity(part),
                title="High claim rejection rate",
                detail=f"Rejection rate {rejection_rate:.1f}% in window",
                metric_value=round(rejection_rate, 1),
            )
        )
    elif rejection_rate >= 10:
        part = 10
        score += part
        signals.append(
            CareGapSignal(
                code="ELEVATED_CLAIM_REJECTION",
                severity=_severity(part),
                title="Elevated claim rejections",
                detail=f"Rejection rate {rejection_rate:.1f}% in window",
                metric_value=round(rejection_rate, 1),
            )
        )

    if low_stock >= 20:
        part = 15
        score += part
        signals.append(
            CareGapSignal(
                code="SUPPLY_GAP",
                severity=_severity(part),
                title="Pharmacy stock gaps",
                detail="Many items at or below minimum quantity",
                metric_value=low_stock,
            )
        )
    elif low_stock >= 5:
        part = 8
        score += part
        signals.append(
            CareGapSignal(
                code="SUPPLY_PRESSURE",
                severity=_severity(part),
                title="Low stock items",
                detail="Inventory pressure across county facilities",
                metric_value=low_stock,
            )
        )

    if emergency_waiting >= 25:
        part = 15
        score += part
        signals.append(
            CareGapSignal(
                code="EMERGENCY_PRESSURE",
                severity=_severity(part),
                title="Emergency department pressure",
                detail="High active emergency visits",
                metric_value=emergency_waiting,
            )
        )

    if occupancy_pct is not None and occupancy_pct >= 90:
        part = 15
        score += part
        signals.append(
            CareGapSignal(
                code="BED_SATURATION",
                severity=_severity(part),
                title="Bed occupancy critical",
                detail=f"Occupancy {occupancy_pct:.0f}%",
                metric_value=round(occupancy_pct, 1),
            )
        )
    elif occupancy_pct is not None and occupancy_pct >= 80:
        part = 8
        score += part
        signals.append(
            CareGapSignal(
                code="BED_PRESSURE",
                severity=_severity(part),
                title="High bed occupancy",
                detail=f"Occupancy {occupancy_pct:.0f}%",
                metric_value=round(occupancy_pct, 1),
            )
        )

    score = min(100, score)
    if not signals:
        signals.append(
            CareGapSignal(
                code="STABLE",
                severity="LOW",
                title="No major gaps detected",
                detail="Aggregate indicators within configured thresholds",
            )
        )
    return score, signals


def build_care_gap_overview(
    db: Session,
    *,
    actor_user_id: UUID,
    window_days: int = 30,
    county: str | None = None,
    top_n: int = 15,
) -> CareGapOverview:
    days = max(7, min(int(window_days or 30), 90))
    top_n = max(1, min(int(top_n or 15), 47))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    county_filter = county.strip() if county else None
    if county_filter == "":
        county_filter = None

    fac_stmt = select(Facility.id, Facility.county).where(Facility.status == "ACTIVE")
    if county_filter:
        fac_stmt = fac_stmt.where(Facility.county == county_filter)
    facilities = db.execute(fac_stmt).all()
    fac_ids = [r[0] for r in facilities]
    county_of: dict[UUID, str] = {r[0]: _county_label(r[1]) for r in facilities}

    # Initialise counties
    counties: dict[str, dict] = {}
    for fid, cname in county_of.items():
        bucket = counties.setdefault(
            cname,
            {
                "facility_count": 0,
                "open_encounters": 0,
                "referral_out": 0,
                "treat_abroad_open": 0,
                "pending_appts": 0,
                "claims_rejected": 0,
                "claims_submitted": 0,
                "low_stock": 0,
                "emergency_waiting": 0,
                "beds_total": 0,
                "beds_occupied": 0,
            },
        )
        bucket["facility_count"] += 1

    if not fac_ids:
        overview = CareGapOverview(
            generated_at=now.isoformat(),
            window_days=days,
            national_gap_score=0,
            counties_scored=0,
            top_gap_counties=[],
            national_signals=[
                CareGapSignal(
                    code="NO_DATA",
                    severity="LOW",
                    title="No active facilities",
                    detail="Cannot score care gaps without ACTIVE facilities",
                )
            ],
            notes=["Aggregate-only view. No patient identifiers exposed."],
        )
        record_audit(
            db,
            action="VIEW_CARE_GAP",
            resource_type="CARE_GAP",
            result="SUCCESS",
            user_id=actor_user_id,
            metadata={"window_days": days, "county": county_filter, "empty": True},
            commit=True,
        )
        return overview

    # Open encounters
    for fid, cnt in db.execute(
        select(Encounter.facility_id, func.count())
        .where(Encounter.facility_id.in_(fac_ids), Encounter.status == "OPEN")
        .group_by(Encounter.facility_id)
    ).all():
        counties[county_of[fid]]["open_encounters"] += int(cnt or 0)

    # Referrals out (from facility) in window
    try:
        for fid, cnt in db.execute(
            select(Referral.from_facility_id, func.count())
            .where(
                Referral.from_facility_id.in_(fac_ids),
                Referral.created_at >= since,
            )
            .group_by(Referral.from_facility_id)
        ).all():
            if fid in county_of:
                counties[county_of[fid]]["referral_out"] += int(cnt or 0)
    except Exception:
        # Schema variants: ignore if column name differs
        pass

    # Treat abroad open
    for fid, cnt in db.execute(
        select(OverseasTreatmentCase.facility_id, func.count())
        .where(
            OverseasTreatmentCase.facility_id.in_(fac_ids),
            OverseasTreatmentCase.status.in_(_OPEN_OTA),
        )
        .group_by(OverseasTreatmentCase.facility_id)
    ).all():
        counties[county_of[fid]]["treat_abroad_open"] += int(cnt or 0)

    # Pending appointment requests
    for fid, cnt in db.execute(
        select(AppointmentRequest.facility_id, func.count())
        .where(
            AppointmentRequest.facility_id.in_(fac_ids),
            AppointmentRequest.status == "PENDING",
        )
        .group_by(AppointmentRequest.facility_id)
    ).all():
        counties[county_of[fid]]["pending_appts"] += int(cnt or 0)

    # Claims via invoices in window
    for fid, status, cnt in db.execute(
        select(Invoice.facility_id, Claim.status, func.count())
        .select_from(Claim)
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .where(Invoice.facility_id.in_(fac_ids), Claim.created_at >= since)
        .group_by(Invoice.facility_id, Claim.status)
    ).all():
        cname = county_of.get(fid)
        if not cname:
            continue
        counties[cname]["claims_submitted"] += int(cnt or 0)
        if str(status).upper() in _REJECTED_CLAIM:
            counties[cname]["claims_rejected"] += int(cnt or 0)

    # Low stock
    for fid, cnt in db.execute(
        select(InventoryItem.facility_id, func.count())
        .where(
            InventoryItem.facility_id.in_(fac_ids),
            InventoryItem.current_quantity <= InventoryItem.minimum_quantity,
        )
        .group_by(InventoryItem.facility_id)
    ).all():
        counties[county_of[fid]]["low_stock"] += int(cnt or 0)

    # Emergency
    for fid, cnt in db.execute(
        select(EmergencyVisit.facility_id, func.count())
        .where(
            EmergencyVisit.facility_id.in_(fac_ids),
            EmergencyVisit.status.in_(_ACTIVE_EMERGENCY),
        )
        .group_by(EmergencyVisit.facility_id)
    ).all():
        counties[county_of[fid]]["emergency_waiting"] += int(cnt or 0)

    # Beds
    for fid, total, occupied in db.execute(
        select(
            Ward.facility_id,
            func.count(Bed.id),
            func.sum(case((Bed.status == "OCCUPIED", 1), else_=0)),
        )
        .join(Bed, Bed.ward_id == Ward.id)
        .where(Ward.facility_id.in_(fac_ids), Ward.status == "ACTIVE")
        .group_by(Ward.facility_id)
    ).all():
        cname = county_of.get(fid)
        if not cname:
            continue
        counties[cname]["beds_total"] += int(total or 0)
        counties[cname]["beds_occupied"] += int(occupied or 0)

    scored: list[CountyCareGap] = []
    for cname, b in counties.items():
        submitted = b["claims_submitted"]
        rejected = b["claims_rejected"]
        rej_rate = (100.0 * rejected / submitted) if submitted else 0.0
        occ = None
        if b["beds_total"] > 0:
            occ = 100.0 * b["beds_occupied"] / b["beds_total"]
        gap_score, signals = _score_county(
            facility_count=b["facility_count"],
            open_encounters=b["open_encounters"],
            referral_out=b["referral_out"],
            treat_abroad_open=b["treat_abroad_open"],
            pending_appts=b["pending_appts"],
            rejection_rate=rej_rate,
            low_stock=b["low_stock"],
            emergency_waiting=b["emergency_waiting"],
            occupancy_pct=occ,
        )
        scored.append(
            CountyCareGap(
                county=cname,
                facility_count=b["facility_count"],
                gap_score=gap_score,
                open_encounters=b["open_encounters"],
                referral_out_30d=b["referral_out"],
                treat_abroad_open=b["treat_abroad_open"],
                appointment_requests_pending=b["pending_appts"],
                claims_rejected_30d=rejected,
                claims_submitted_30d=submitted,
                rejection_rate_pct=round(rej_rate, 1),
                low_stock_items=b["low_stock"],
                emergency_waiting=b["emergency_waiting"],
                bed_occupancy_pct=round(occ, 1) if occ is not None else None,
                signals=signals,
            )
        )

    scored.sort(key=lambda x: (-x.gap_score, x.county))
    top = scored[:top_n]
    national_score = int(round(sum(c.gap_score for c in scored) / max(len(scored), 1)))

    national_signals: list[CareGapSignal] = []
    critical_counties = [c for c in scored if c.gap_score >= 60]
    if critical_counties:
        national_signals.append(
            CareGapSignal(
                code="COUNTIES_IN_CRITICAL_GAP",
                severity="CRITICAL",
                title="Counties with severe care gaps",
                detail=", ".join(c.county for c in critical_counties[:8]),
                metric_value=len(critical_counties),
            )
        )
    high_reject = [c for c in scored if c.rejection_rate_pct >= 20 and c.claims_submitted_30d >= 5]
    if high_reject:
        national_signals.append(
            CareGapSignal(
                code="NATIONAL_CLAIM_QUALITY",
                severity="HIGH",
                title="Claim rejection hotspots",
                detail=f"{len(high_reject)} counties above 20% rejection",
                metric_value=len(high_reject),
            )
        )
    if not national_signals:
        national_signals.append(
            CareGapSignal(
                code="NATIONAL_STABLE",
                severity="LOW",
                title="No national critical gap flags",
                detail="County scores within operational bands",
            )
        )

    overview = CareGapOverview(
        generated_at=now.isoformat(),
        window_days=days,
        national_gap_score=national_score,
        counties_scored=len(scored),
        top_gap_counties=top,
        national_signals=national_signals,
        notes=[
            "Aggregate-only. No patient IDs, names, or clinical free-text.",
            "Scores are operational heuristics for MOH/county prioritisation — not clinical diagnoses.",
            f"Window: last {days} days where time-bounded.",
        ],
    )
    record_audit(
        db,
        action="VIEW_CARE_GAP",
        resource_type="CARE_GAP",
        result="SUCCESS",
        user_id=actor_user_id,
        metadata={
            "window_days": days,
            "county": county_filter,
            "counties_scored": len(scored),
            "national_gap_score": national_score,
        },
        commit=True,
    )
    return overview
