"""Imaging Intelligence — contrast safety, critical findings, TAT."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import Allergy
from app.imaging_intelligence.models import ImagingCriticalFinding, ImagingTestSafety
from app.radiology.models import ImagingOrder, ImagingReport, ImagingTest

logger = logging.getLogger("afyasync.imaging_intelligence")

_CONTRAST_ALLERGENS = {
    "IODINE": ("iodine", "iodinated", "contrast", "omnipaque", "ultravist"),
    "GADOLINIUM": ("gadolinium", "gadovist", "dotarem", "contrast"),
}


def check_contrast_safety(
    db: Session,
    *,
    patient_id: UUID,
    test_id: UUID,
) -> dict:
    """Pre-order check: contrast allergy risk."""
    safety = db.scalar(
        select(ImagingTestSafety).where(
            ImagingTestSafety.test_id == test_id,
            ImagingTestSafety.status == "ACTIVE",
        )
    )
    test = db.get(ImagingTest, test_id)
    warnings: list[str] = []
    blocking = False

    if safety is None or not safety.requires_contrast:
        return {
            "test_id": str(test_id),
            "requires_contrast": False,
            "can_proceed": True,
            "blocking": False,
            "warnings": [],
        }

    allergies = list(
        db.scalars(
            select(Allergy).where(
                Allergy.patient_id == patient_id,
                Allergy.status == "ACTIVE",
            )
        )
    )
    ctype = (_CONTRAST_ALLERGENS.get((safety.contrast_type or "").upper()) or ()) + ("contrast",)
    for allergy in allergies:
        a = (allergy.allergen or "").casefold()
        if any(tok in a or a in tok for tok in tokens):
            sev = (allergy.severity or "").upper()
            msg = f"Documented allergy '{allergy.allergen}' may conflict with {safety.contrast_type or 'contrast'} media"
            warnings.append(msg)
            if sev in {"SEVERE", "LIFE_THREATENING"}:
                blocking = True

    if safety.pregnancy_caution:
        warnings.append("Study flagged for pregnancy caution — confirm status before exposure")

    return {
        "test_id": str(test_id),
        "test_name": test.name if test else None,
        "requires_contrast": True,
        "contrast_type": safety.contrast_type,
        "can_proceed": not blocking,
        "blocking": blocking,
        "warnings": warnings,
    }


def assert_can_order_imaging(
    db: Session,
    *,
    patient_id: UUID,
    test_id: UUID,
    override_reason: str | None = None,
) -> dict:
    result = check_contrast_safety(db, patient_id=patient_id, test_id=test_id)
    if result["blocking"]:
        reason = (override_reason or "").strip()
        if len(reason) < 15:
            raise ValueError("CONTRAST_SAFETY_OVERRIDE_REQUIRED")
    return result


def register_critical_finding(
    db: Session,
    *,
    report: ImagingReport,
    order: ImagingOrder,
    test: ImagingTest,
    summary: str,
    actor_user_id: UUID | None = None,
) -> ImagingCriticalFinding:
    summary = (summary or "").strip()
    if len(summary) < 5:
        raise ValueError("CRITICAL_FINDING_SUMMARY_REQUIRED")

    existing = db.scalar(
        select(ImagingCriticalFinding).where(ImagingCriticalFinding.report_id == report.id)
    )
    if existing:
        return existing

    finding = ImagingCriticalFinding(
        report_id=report.id,
        order_id=order.id,
        facility_id=order.facility_id,
        patient_id=order.patient_id,
        modality=test.modality if test else None,
        test_name=test.name if test else "Imaging",
        summary=summary[:2000],
        severity="CRITICAL",
        status="OPEN",
    )
    db.add(finding)
    db.flush()
    record_audit(
        db,
        action="IMAGING_CRITICAL_FINDING",
        resource_type="IMAGING_REPORT",
        resource_id=str(report.id),
        result="CRITICAL",
        user_id=actor_user_id,
        facility_id=order.facility_id,
        patient_id=order.patient_id,
        metadata={"finding_id": str(finding.id)},
        commit=False,
    )
    return finding


def acknowledge_finding(
    db: Session,
    *,
    finding_id: UUID,
    facility_id: UUID,
    staff_id: UUID,
    note: str | None,
    actor_user_id: UUID | None = None,
) -> ImagingCriticalFinding:
    row = db.get(ImagingCriticalFinding, finding_id)
    if row is None or row.facility_id != facility_id:
        raise ValueError("FINDING_NOT_FOUND")
    if row.status != "OPEN":
        raise ValueError("FINDING_NOT_OPEN")
    row.status = "ACKNOWLEDGED"
    row.acknowledged_by = staff_id
    row.acknowledged_at = datetime.now(timezone.utc)
    row.ack_note = (note or "").strip() or None
    db.flush()
    record_audit(
        db,
        action="IMAGING_CRITICAL_ACK",
        resource_type="IMAGING_CRITICAL_FINDING",
        resource_id=str(row.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=row.patient_id,
        commit=False,
    )
    return row


def list_open_findings(db: Session, facility_id: UUID, *, limit: int = 50) -> list[ImagingCriticalFinding]:
    limit = min(max(limit, 1), 200)
    return list(
        db.scalars(
            select(ImagingCriticalFinding)
            .where(
                ImagingCriticalFinding.facility_id == facility_id,
                ImagingCriticalFinding.status == "OPEN",
            )
            .order_by(ImagingCriticalFinding.created_at.desc())
            .limit(limit)
        )
    )


def imaging_tat_summary(db: Session, facility_id: UUID, *, days: int = 7) -> dict:
    days = min(max(days, 1), 90)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(ImagingOrder.ordered_at, ImagingOrder.completed_at)
        .where(
            ImagingOrder.facility_id == facility_id,
            ImagingOrder.completed_at.is_not(None),
            ImagingOrder.ordered_at >= since,
        )
        .limit(500)
    ).all()
    deltas = []
    for ordered_at, completed_at in rows:
        if ordered_at and completed_at:
            d = (completed_at - ordered_at).total_seconds() / 60.0
            if d >= 0:
                deltas.append(d)
    deltas.sort()
    n = len(deltas)
    if n == 0:
        return {
            "facility_id": str(facility_id),
            "days": days,
            "sample_size": 0,
            "median_minutes": None,
            "p90_minutes": None,
        }
    return {
        "facility_id": str(facility_id),
        "days": days,
        "sample_size": n,
        "median_minutes": round(deltas[n // 2], 1),
        "p90_minutes": round(deltas[min(n - 1, int(n * 0.9))], 1),
        "notes": ["Order-to-report TAT"],
    }


def upsert_test_safety(db: Session, *, test_id: UUID, data: dict) -> ImagingTestSafety:
    test = db.get(ImagingTest, test_id)
    if test is None:
        raise ValueError("IMAGING_TEST_NOT_FOUND")
    row = db.scalar(select(ImagingTestSafety).where(ImagingTestSafety.test_id == test_id))
    if row is None:
        row = ImagingTestSafety(test_id=test_id)
        db.add(row)
    for key in ("requires_contrast", "contrast_type", "radiation_risk", "pregnancy_caution", "notes"):
        if key in data and data[key] is not None:
            setattr(row, key, data[key])
    row.status = "ACTIVE"
    db.flush()
    return row
