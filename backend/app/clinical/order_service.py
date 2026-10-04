"""Phase 132 — place and manage clinical orders. Developed by BAHATI GAD WANGWE."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.order_models import ClinicalOrder
from app.encounters.models import Encounter

ORDER_TYPES = {"LAB", "PHARMACY", "IMAGING"}
PRIORITIES = {"ROUTINE", "URGENT", "STAT"}
STATUSES = {"ORDERED", "IN_PROGRESS", "COMPLETED", "CANCELLED"}


class OrderError(ValueError):
    pass


def _open_encounter(db: Session, encounter_id: UUID, facility_id: UUID) -> Encounter:
    enc = db.get(Encounter, encounter_id)
    if enc is None:
        raise OrderError("ENCOUNTER_NOT_FOUND")
    if enc.facility_id != facility_id:
        raise OrderError("FACILITY_ACCESS_DENIED")
    if enc.status in {"CLOSED", "DISCHARGED", "CANCELLED"}:
        raise OrderError("ENCOUNTER_CLOSED")
    return enc


def list_orders(
    db: Session,
    *,
    encounter_id: UUID,
    facility_id: UUID,
    order_type: str | None = None,
) -> list[ClinicalOrder]:
    enc = db.get(Encounter, encounter_id)
    if enc is None:
        raise OrderError("ENCOUNTER_NOT_FOUND")
    if enc.facility_id != facility_id:
        raise OrderError("FACILITY_ACCESS_DENIED")
    q = select(ClinicalOrder).where(ClinicalOrder.encounter_id == encounter_id)
    if order_type:
        q = q.where(ClinicalOrder.order_type == order_type.upper())
    return list(db.scalars(q.order_by(ClinicalOrder.ordered_at.desc())).all())


def create_order(
    db: Session,
    *,
    encounter_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None,
    order_type: str,
    description: str,
    code: str | None = None,
    priority: str = "ROUTINE",
    notes: str | None = None,
) -> ClinicalOrder:
    enc = _open_encounter(db, encounter_id, facility_id)
    order_type = (order_type or "").strip().upper()
    priority = (priority or "ROUTINE").strip().upper()
    description = (description or "").strip()
    if order_type not in ORDER_TYPES:
        raise OrderError("INVALID_ORDER_TYPE")
    if priority not in PRIORITIES:
        raise OrderError("INVALID_PRIORITY")
    if len(description) < 2:
        raise OrderError("DESCRIPTION_REQUIRED")

    row = ClinicalOrder(
        encounter_id=enc.id,
        facility_id=enc.facility_id,
        patient_id=enc.patient_id,
        order_type=order_type,
        code=(code or None),
        description=description,
        priority=priority,
        status="ORDERED",
        notes=notes,
        ordered_by=actor_user_id,
    )
    db.add(row)
    record_audit(
        db,
        action="CLINICAL_ORDER_CREATE",
        resource_type="CLINICAL_ORDER",
        resource_id=str(enc.id),
        result="ORDERED",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=enc.patient_id,
        metadata={"order_type": order_type, "priority": priority, "code": code},
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return row


def update_order_status(
    db: Session,
    *,
    order_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None,
    status: str,
) -> ClinicalOrder:
    status = (status or "").strip().upper()
    if status not in STATUSES:
        raise OrderError("INVALID_STATUS")
    row = db.get(ClinicalOrder, order_id)
    if row is None:
        raise OrderError("ORDER_NOT_FOUND")
    if row.facility_id != facility_id:
        raise OrderError("FACILITY_ACCESS_DENIED")
    if row.status == "CANCELLED" and status != "CANCELLED":
        raise OrderError("ORDER_CANCELLED")
    row.status = status
    row.updated_at = datetime.now(timezone.utc)
    record_audit(
        db,
        action="CLINICAL_ORDER_STATUS",
        resource_type="CLINICAL_ORDER",
        resource_id=str(row.id),
        result=status,
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=row.patient_id,
        metadata={"order_type": row.order_type},
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return row


def order_to_dict(row: ClinicalOrder) -> dict:
    return {
        "id": str(row.id),
        "encounter_id": str(row.encounter_id),
        "patient_id": str(row.patient_id),
        "order_type": row.order_type,
        "code": row.code,
        "description": row.description,
        "priority": row.priority,
        "status": row.status,
        "notes": row.notes,
        "ordered_at": row.ordered_at.isoformat() if row.ordered_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "developer": "BAHATI GAD WANGWE",
    }
