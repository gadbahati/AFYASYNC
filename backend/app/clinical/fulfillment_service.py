"""Phase 133 — fulfill / complete clinical orders. Developed by BAHATI GAD WANGWE."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.order_models import ClinicalOrder
from app.clinical.order_service import OrderError, STATUSES


def fulfill_order(
    db: Session,
    *,
    order_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None,
    status: str = "COMPLETED",
    result_notes: str | None = None,
) -> ClinicalOrder:
    """Mark order IN_PROGRESS / COMPLETED / CANCELLED with optional result notes."""
    status = (status or "COMPLETED").strip().upper()
    if status not in STATUSES:
        raise OrderError("INVALID_STATUS")
    if status == "ORDERED":
        raise OrderError("INVALID_FULFILLMENT_STATUS")

    row = db.get(ClinicalOrder, order_id)
    if row is None:
        raise OrderError("ORDER_NOT_FOUND")
    if row.facility_id != facility_id:
        raise OrderError("FACILITY_ACCESS_DENIED")
    if row.status == "CANCELLED":
        raise OrderError("ORDER_CANCELLED")
    if row.status == "COMPLETED" and status != "COMPLETED":
        raise OrderError("ORDER_ALREADY_COMPLETED")

    row.status = status
    row.updated_at = datetime.now(timezone.utc)
    if result_notes and str(result_notes).strip():
        note = str(result_notes).strip()[:2000]
        prefix = f"[{status}] {note}"
        row.notes = f"{row.notes}\n{prefix}".strip() if row.notes else prefix

    record_audit(
        db,
        action="CLINICAL_ORDER_FULFILL",
        resource_type="CLINICAL_ORDER",
        resource_id=str(row.id),
        result=status,
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=row.patient_id,
        metadata={
            "order_type": row.order_type,
            "code": row.code,
            "has_result": bool(result_notes),
        },
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return row
