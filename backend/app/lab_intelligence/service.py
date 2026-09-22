"""Laboratory Intelligence — evaluate results, critical alerts, TAT."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.lab_intelligence.models import LabCriticalAlert, LabTestReference
from app.laboratory.models import LabOrder, LabOrderItem, LabResult, LabTest
from app.notifications.events import notify_patient_event

logger = logging.getLogger("afyasync.lab_intelligence")


def _parse_numeric(raw: str) -> Decimal | None:
    if raw is None:
        return None
    s = str(raw).strip().replace(",", "")
    for prefix in (">", "<", "=", "~"):
        if s.startswith(prefix):
            s = s[1:].strip()
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def evaluate_result_against_reference(
    db: Session,
    *,
    result: LabResult,
    test: LabTest,
    facility_id: UUID,
    patient_id: UUID,
    encounter_id: UUID,
    actor_user_id: UUID | None = None,
) -> LabCriticalAlert | None:
    """Compare numeric result to reference; OPEN alert only for critical/panic values."""
    ref = db.scalar(
        select(LabTestReference).where(
            LabTestReference.test_id == test.id,
            LabTestReference.status == "ACTIVE",
        )
    )
    if ref is None:
        return None

    value = _parse_numeric(result.result)
    if value is None:
        return None

    # Always fill reference text when available
    if not result.reference_range and ref.ref_low is not None and ref.ref_high is not None:
        result.reference_range = f"{ref.ref_low} – {ref.ref_high}"
        if ref.unit:
            result.unit = result.unit or ref.unit

    flag = None
    severity = None
    if ref.critical_low is not None and value <= Decimal(str(ref.critical_low)):
        flag, severity = "CRITICAL_LOW", "CRITICAL"
    elif ref.critical_high is not None and value >= Decimal(str(ref.critical_high)):
        flag, severity = "CRITICAL_HIGH", "CRITICAL"
    elif ref.ref_low is not None and value < Decimal(str(ref.ref_low)):
        flag, severity = "ABNORMAL_LOW", "ABNORMAL"
    elif ref.ref_high is not None and value > Decimal(str(ref.ref_high)):
        flag, severity = "ABNORMAL_HIGH", "ABNORMAL"

    if flag is None:
        return None

    # Informational abnormal: audit only, no mandatory inbox item
    if severity == "ABNORMAL":
        record_audit(
            db,
            action="LAB_ABNORMAL_RESULT",
            resource_type="LAB_RESULT",
            resource_id=str(result.id),
            result="ABNORMAL",
            user_id=actor_user_id,
            facility_id=facility_id,
            patient_id=patient_id,
            metadata={"flag": flag, "value": str(value), "test": test.code},
            commit=False,
        )
        return None

    existing = db.scalar(
        select(LabCriticalAlert).where(LabCriticalAlert.lab_result_id == result.id)
    )
    if existing:
        return existing

    alert = LabCriticalAlert(
        lab_result_id=result.id,
        facility_id=facility_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        test_code=test.code,
        test_name=test.name,
        result_value=str(result.result),
        unit=result.unit or ref.unit,
        flag=flag,
        severity="CRITICAL",
        status="OPEN",
    )
    db.add(alert)
    db.flush()

    record_audit(
        db,
        action="LAB_CRITICAL_ALERT",
        resource_type="LAB_RESULT",
        resource_id=str(result.id),
        result="CRITICAL",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={"flag": flag, "value": str(value), "test": test.code},
        commit=False,
    )

    try:
        notify_patient_event(
            db,
            patient_id=patient_id,
            facility_id=facility_id,
            event_type="LAB_CRITICAL_VALUE",
            action_url=f"/facility/lab/critical/{alert.id}",
            priority="HIGH",
            metadata={"test": test.code, "flag": flag, "value": str(result.result)},
            actor_user_id=actor_user_id,
            commit=False,
        )
    except Exception:
        logger.exception("Failed to notify on lab critical alert")

    return alert


def on_lab_result_entered(
    db: Session,
    *,
    result: LabResult,
    facility_id: UUID,
    patient_id: UUID,
    encounter_id: UUID,
    test_id: UUID,
    actor_user_id: UUID | None = None,
) -> LabCriticalAlert | None:
    test = db.get(LabTest, test_id)
    if test is None:
        return None
    try:
        return evaluate_result_against_reference(
            db,
            result=result,
            test=test,
            facility_id=facility_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            actor_user_id=actor_user_id,
        )
    except Exception:
        logger.exception("Lab intelligence evaluation failed for result %s", result.id)
        return None


def acknowledge_critical(
    db: Session,
    *,
    alert_id: UUID,
    facility_id: UUID,
    staff_id: UUID,
    note: str | None,
    actor_user_id: UUID | None = None,
) -> LabCriticalAlert:
    alert = db.get(LabCriticalAlert, alert_id)
    if alert is None or alert.facility_id != facility_id:
        raise ValueError("ALERT_NOT_FOUND")
    if alert.status != "OPEN":
        raise ValueError("ALERT_NOT_OPEN")
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_by = staff_id
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.ack_note = (note or "").strip() or None
    db.flush()
    record_audit(
        db,
        action="LAB_CRITICAL_ACK",
        resource_type="LAB_CRITICAL_ALERT",
        resource_id=str(alert.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=alert.patient_id,
        metadata={"flag": alert.flag},
        commit=False,
    )
    return alert


def list_open_criticals(db: Session, facility_id: UUID, *, limit: int = 50) -> list[LabCriticalAlert]:
    limit = min(max(limit, 1), 200)
    return list(
        db.scalars(
            select(LabCriticalAlert)
            .where(
                LabCriticalAlert.facility_id == facility_id,
                LabCriticalAlert.status == "OPEN",
                LabCriticalAlert.severity == "CRITICAL",
            )
            .order_by(LabCriticalAlert.created_at.desc())
            .limit(limit)
        )
    )


def tat_summary(db: Session, facility_id: UUID, *, days: int = 7) -> dict:
    from datetime import timedelta

    from app.encounters.models import Encounter

    days = min(max(days, 1), 90)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.execute(
        select(LabOrder.created_at, LabResult.created_at, LabOrder.priority)
        .join(LabOrderItem, LabOrderItem.lab_order_id == LabOrder.id)
        .join(LabResult, LabResult.lab_order_item_id == LabOrderItem.id)
        .join(Encounter, Encounter.id == LabOrder.encounter_id)
        .where(
            Encounter.facility_id == facility_id,
            LabResult.created_at >= since,
        )
        .limit(500)
    ).all()

    if not rows:
        return {
            "facility_id": str(facility_id),
            "days": days,
            "sample_size": 0,
            "median_minutes": None,
            "p90_minutes": None,
            "notes": ["No results in window"],
        }

    deltas = []
    for ordered_at, resulted_at, _pri in rows:
        if ordered_at and resulted_at:
            delta = (resulted_at - ordered_at).total_seconds() / 60.0
            if delta >= 0:
                deltas.append(delta)
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

    median = deltas[n // 2]
    p90 = deltas[min(n - 1, int(n * 0.9))]
    return {
        "facility_id": str(facility_id),
        "days": days,
        "sample_size": n,
        "median_minutes": round(median, 1),
        "p90_minutes": round(p90, 1),
        "notes": ["Order-to-result TAT"],
    }


def upsert_test_reference(db: Session, *, test_id: UUID, data: dict) -> LabTestReference:
    test = db.get(LabTest, test_id)
    if test is None or test.status != "ACTIVE":
        raise ValueError("LAB_TEST_NOT_FOUND")
    # Sanity: critical bounds must be outside or equal to reference if both set
    ref_low = data.get("ref_low")
    ref_high = data.get("ref_high")
    crit_low = data.get("critical_low")
    crit_high = data.get("critical_high")
    if ref_low is not None and ref_high is not None and Decimal(str(ref_low)) > Decimal(str(ref_high)):
        raise ValueError("INVALID_REFERENCE_RANGE")
    if crit_low is not None and ref_low is not None and Decimal(str(crit_low)) > Decimal(str(ref_low)):
        raise ValueError("CRITICAL_LOW_MUST_BE_LE_REF_LOW")
    if crit_high is not None and ref_high is not None and Decimal(str(crit_high)) < Decimal(str(ref_high)):
        raise ValueError("CRITICAL_HIGH_MUST_BE_GE_REF_HIGH")

    row = db.scalar(select(LabTestReference).where(LabTestReference.test_id == test_id))
    if row is None:
        row = LabTestReference(test_id=test_id)
        db.add(row)
    for key in (
        "unit",
        "ref_low",
        "ref_high",
        "critical_low",
        "critical_high",
        "tat_target_minutes",
        "sex_specific",
        "notes",
    ):
        if key in data and data[key] is not None:
            setattr(row, key, data[key])
    row.status = "ACTIVE"
    db.flush()
    return row
