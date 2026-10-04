"""Phase 133/146 — fulfill clinical orders + optional encounter clinical note.

Developed by BAHATI GAD WANGWE.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.order_models import ClinicalOrder
from app.clinical.order_service import OrderError, STATUSES


def _append_encounter_note(
    db: Session,
    *,
    row: ClinicalOrder,
    actor_user_id: UUID | None,
    status: str,
    result_notes: str,
) -> None:
    """Phase 146 — surface fulfillment on the encounter clinical record."""
    try:
        from app.clinical.schemas import ClinicalNoteCreate
        from app.clinical.service import save_clinical_note
    except Exception:
        return

    content = (
        f"Clinical order {row.order_type} "
        f"({row.code or 'n/a'}) marked {status}.\n"
        f"{row.description or ''}\n"
        f"Result: {result_notes.strip()}"
    ).strip()
    if len(content) > 20000:
        content = content[:19997] + "..."

    note_type = "SPECIALIST" if row.order_type in {"IMAGING", "LAB", "LABORATORY"} else "PROGRESS"
    try:
        payload = ClinicalNoteCreate(
            note_type=note_type,
            content=content,
            status="FINAL",
        )
        save_clinical_note(
            db,
            row.encounter_id,
            payload,
            actor_user_id=actor_user_id,
        )
    except Exception:
        # Do not roll back order fulfillment if note write fails
        pass


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
    notes_text = None
    if result_notes and str(result_notes).strip():
        notes_text = str(result_notes).strip()[:2000]
        prefix = f"[{status}] {notes_text}"
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
            "encounter_note": bool(notes_text and status == "COMPLETED"),
        },
        commit=False,
    )

    # Phase 146 — write encounter clinical note when completing with results
    if status == "COMPLETED" and notes_text:
        _append_encounter_note(
            db,
            row=row,
            actor_user_id=actor_user_id,
            status=status,
            result_notes=notes_text,
        )

    db.commit()
    db.refresh(row)
    return row
