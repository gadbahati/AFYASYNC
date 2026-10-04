"""Phase 133/146/147 — fulfill clinical orders + structured report fields.

Developed by BAHATI GAD WANGWE.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.order_models import ClinicalOrder
from app.clinical.order_service import OrderError, STATUSES


def _format_result_block(
    *,
    result_notes: str | None,
    modality: str | None,
    impression: str | None,
) -> str | None:
    """Phase 147 — combine free text + structured radiology fields."""
    parts: list[str] = []
    if modality and str(modality).strip():
        parts.append(f"Modality: {str(modality).strip()[:80]}")
    if impression and str(impression).strip():
        parts.append(f"Impression: {str(impression).strip()[:4000]}")
    if result_notes and str(result_notes).strip():
        parts.append(str(result_notes).strip()[:2000])
    if not parts:
        return None
    return "\n".join(parts)


def _append_encounter_note(
    db: Session,
    *,
    row: ClinicalOrder,
    actor_user_id: UUID | None,
    status: str,
    result_notes: str,
) -> None:
    """Surface fulfillment on the encounter clinical record."""
    try:
        from app.clinical.models import ClinicalNote
    except Exception:
        return

    body = (
        f"Clinical order {row.order_type} "
        f"({row.code or 'n/a'}) marked {status}.\n"
        f"{row.description or ''}\n"
        f"{result_notes.strip()}"
    ).strip()
    if len(body) > 20000:
        body = body[:19997] + "..."

    note_type = "SPECIALIST" if row.order_type in {"IMAGING", "LAB", "LABORATORY"} else "PROGRESS"
    try:
        note = ClinicalNote(
            encounter_id=row.encounter_id,
            note_type=note_type,
            body=body,
            author_id=actor_user_id,
        )
        db.add(note)
        db.flush()
        record_audit(
            db,
            action="CLINICAL_NOTE_CREATED",
            resource_type="CLINICAL_NOTE",
            resource_id=str(note.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=row.facility_id,
            patient_id=row.patient_id,
            metadata={"source": "ORDER_FULFILL", "order_id": str(row.id)},
            commit=False,
        )
    except Exception:
        pass


def fulfill_order(
    db: Session,
    *,
    order_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None,
    status: str = "COMPLETED",
    result_notes: str | None = None,
    modality: str | None = None,
    impression: str | None = None,
) -> ClinicalOrder:
    """Mark order IN_PROGRESS / COMPLETED / CANCELLED with optional structured results."""
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

    notes_text = _format_result_block(
        result_notes=result_notes,
        modality=modality,
        impression=impression,
    )

    row.status = status
    row.updated_at = datetime.now(timezone.utc)
    if notes_text:
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
            "has_result": bool(notes_text),
            "modality": (modality or "")[:80] or None,
            "has_impression": bool(impression and str(impression).strip()),
            "encounter_note": bool(notes_text and status == "COMPLETED"),
        },
        commit=False,
    )

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
