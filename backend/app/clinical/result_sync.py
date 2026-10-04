"""Phase 135 — sync department outcomes back to clinical orders.

Developed by BAHATI GAD WANGWE.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.order_models import ClinicalOrder


def complete_clinical_orders_for_encounter(
    db: Session,
    *,
    encounter_id: UUID,
    facility_id: UUID,
    order_type: str,
    result_summary: str,
    actor_user_id: UUID | None = None,
    patient_id: UUID | None = None,
) -> int:
    """Mark matching open clinical orders COMPLETED with result notes.

    Matches ORDERED / IN_PROGRESS rows of the given type on the encounter.
    Returns number of clinical orders updated.
    """
    rows = list(
        db.scalars(
            select(ClinicalOrder).where(
                ClinicalOrder.encounter_id == encounter_id,
                ClinicalOrder.facility_id == facility_id,
                ClinicalOrder.order_type == order_type,
                ClinicalOrder.status.in_(("ORDERED", "IN_PROGRESS")),
            )
        )
    )
    if not rows:
        return 0

    now = datetime.now(timezone.utc)
    summary = (result_summary or "")[:1500]
    for row in rows:
        row.status = "COMPLETED"
        row.updated_at = now
        note = f"[DEPT_RESULT] {summary}"
        row.notes = f"{row.notes}\n{note}".strip() if row.notes else note
        record_audit(
            db,
            action="CLINICAL_ORDER_DEPT_SYNC",
            resource_type="CLINICAL_ORDER",
            resource_id=str(row.id),
            result="COMPLETED",
            user_id=actor_user_id,
            facility_id=facility_id,
            patient_id=patient_id or row.patient_id,
            metadata={"order_type": order_type, "source": "department_result"},
            commit=False,
        )
    return len(rows)


def complete_clinical_order_by_link_note(
    db: Session,
    *,
    linked_token: str,
    facility_id: UUID,
    result_summary: str,
    actor_user_id: UUID | None = None,
) -> int:
    """Complete clinical orders whose notes contain a linked department id token."""
    if not linked_token:
        return 0
    rows = list(
        db.scalars(
            select(ClinicalOrder).where(
                ClinicalOrder.facility_id == facility_id,
                ClinicalOrder.status.in_(("ORDERED", "IN_PROGRESS")),
                ClinicalOrder.notes.is_not(None),
            )
        )
    )
    matched = [r for r in rows if linked_token in (r.notes or "")]
    now = datetime.now(timezone.utc)
    summary = (result_summary or "")[:1500]
    for row in matched:
        row.status = "COMPLETED"
        row.updated_at = now
        note = f"[DEPT_RESULT] {summary}"
        row.notes = f"{row.notes}\n{note}".strip()
        record_audit(
            db,
            action="CLINICAL_ORDER_DEPT_SYNC",
            resource_type="CLINICAL_ORDER",
            resource_id=str(row.id),
            result="COMPLETED",
            user_id=actor_user_id,
            facility_id=facility_id,
            patient_id=row.patient_id,
            metadata={"linked_token": linked_token},
            commit=False,
        )
    return len(matched)
