"""Phase 134 — forward clinical orders into lab/pharmacy departments.

Developed by BAHATI GAD WANGWE.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.order_models import ClinicalOrder
from app.clinical.order_service import OrderError, order_to_dict
from app.encounters.models import Encounter
from app.rbac.models import Staff


def _staff_for_user(db: Session, user_id: UUID, facility_id: UUID) -> Staff | None:
    return db.scalar(
        select(Staff).where(
            Staff.user_id == user_id,
            Staff.facility_id == facility_id,
            Staff.status == "ACTIVE",
        ).limit(1)
    )


def forward_clinical_order(
    db: Session,
    *,
    order_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None,
) -> dict:
    """Create linked lab order or pharmacy prescription when catalog match exists."""
    row = db.get(ClinicalOrder, order_id)
    if row is None:
        raise OrderError("ORDER_NOT_FOUND")
    if row.facility_id != facility_id:
        raise OrderError("FACILITY_ACCESS_DENIED")
    if row.status in {"COMPLETED", "CANCELLED"}:
        raise OrderError("ORDER_NOT_FORWARDABLE")

    enc = db.get(Encounter, row.encounter_id)
    if enc is None:
        raise OrderError("ENCOUNTER_NOT_FOUND")
    if enc.status in {"CLOSED", "DISCHARGED", "CANCELLED"}:
        raise OrderError("ENCOUNTER_CLOSED")

    staff = _staff_for_user(db, actor_user_id, facility_id) if actor_user_id else None
    linked: dict = {"department": None, "linked_id": None, "matched": False, "message": ""}

    if row.order_type == "LAB":
        linked = _forward_lab(db, row=row, enc=enc, staff=staff, actor_user_id=actor_user_id)
    elif row.order_type == "PHARMACY":
        linked = _forward_pharmacy(db, row=row, enc=enc, staff=staff, actor_user_id=actor_user_id)
    elif row.order_type == "IMAGING":
        # Imaging department module may exist separately — mark in progress for worklist
        row.status = "IN_PROGRESS"
        note = "[FORWARDED:IMAGING] Awaiting radiology worklist"
        row.notes = f"{row.notes}\n{note}".strip() if row.notes else note
        row.updated_at = datetime.now(timezone.utc)
        linked = {
            "department": "IMAGING",
            "linked_id": None,
            "matched": False,
            "message": "Imaging order marked IN_PROGRESS for radiology queue",
        }
    else:
        raise OrderError("INVALID_ORDER_TYPE")

    if row.status == "ORDERED":
        row.status = "IN_PROGRESS"
    row.updated_at = datetime.now(timezone.utc)

    record_audit(
        db,
        action="CLINICAL_ORDER_FORWARD",
        resource_type="CLINICAL_ORDER",
        resource_id=str(row.id),
        result=row.status,
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=row.patient_id,
        metadata=linked,
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return {"order": order_to_dict(row), "forward": linked, "developer": "BAHATI GAD WANGWE"}


def _forward_lab(
    db: Session,
    *,
    row: ClinicalOrder,
    enc: Encounter,
    staff: Staff | None,
    actor_user_id: UUID | None,
) -> dict:
    from app.laboratory.models import LabOrder, LabOrderItem, LabTest

    code = (row.code or "").strip().upper()
    test = None
    if code:
        test = db.scalar(select(LabTest).where(func.upper(LabTest.code) == code, LabTest.status == "ACTIVE"))
    if test is None and row.description:
        # fuzzy name match
        test = db.scalar(
            select(LabTest).where(
                LabTest.status == "ACTIVE",
                func.lower(LabTest.name).contains(row.description.strip().lower()[:40]),
            ).limit(1)
        )

    if test is None:
        note = f"[FORWARDED:LAB] No catalog match for code={row.code!r}; kept on clinical worklist"
        row.notes = f"{row.notes}\n{note}".strip() if row.notes else note
        return {
            "department": "LAB",
            "linked_id": None,
            "matched": False,
            "message": "No matching LabTest in catalog — order stays clinical until cataloged",
        }

    if staff is None:
        raise OrderError("STAFF_REQUIRED_FOR_LAB_FORWARD")

    priority_map = {"ROUTINE": "NORMAL", "URGENT": "URGENT", "STAT": "STAT"}
    lab = LabOrder(
        order_id=f"LAB-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{str(uuid4())[:6].upper()}",
        encounter_id=enc.id,
        patient_id=enc.patient_id,
        ordered_by=staff.id,
        priority=priority_map.get(row.priority, "NORMAL"),
        status="ORDERED",
    )
    db.add(lab)
    db.flush()
    db.add(
        LabOrderItem(
            lab_order_id=lab.id,
            test_id=test.id,
            instructions=row.notes or row.description,
        )
    )
    note = f"[FORWARDED:LAB] linked_lab_order={lab.id} order_id={lab.order_id} test={test.code}"
    row.notes = f"{row.notes}\n{note}".strip() if row.notes else note
    if actor_user_id:
        record_audit(
            db,
            action="LAB_ORDER_CREATED",
            resource_type="LAB_ORDER",
            resource_id=str(lab.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=enc.facility_id,
            patient_id=enc.patient_id,
            metadata={"from_clinical_order": str(row.id), "order_id": lab.order_id},
            commit=False,
        )
    return {
        "department": "LAB",
        "linked_id": str(lab.id),
        "lab_order_id": lab.order_id,
        "test_code": test.code,
        "matched": True,
        "message": f"Lab order {lab.order_id} created for test {test.code}",
    }


def _forward_pharmacy(
    db: Session,
    *,
    row: ClinicalOrder,
    enc: Encounter,
    staff: Staff | None,
    actor_user_id: UUID | None,
) -> dict:
    from app.pharmacy.models import Medication, Prescription, PrescriptionItem

    med = None
    code = (row.code or "").strip()
    if code:
        med = db.scalar(
            select(Medication).where(
                (func.upper(Medication.code) == code.upper()) | (func.lower(Medication.name) == code.lower())
            ).limit(1)
        )
    if med is None and row.description:
        med = db.scalar(
            select(Medication).where(func.lower(Medication.name).contains(row.description.strip().lower()[:40])).limit(1)
        )

    if med is None:
        note = f"[FORWARDED:PHARMACY] No medication match for code={row.code!r}"
        row.notes = f"{row.notes}\n{note}".strip() if row.notes else note
        return {
            "department": "PHARMACY",
            "linked_id": None,
            "matched": False,
            "message": "No matching Medication — order stays clinical until cataloged",
        }

    if staff is None:
        raise OrderError("STAFF_REQUIRED_FOR_PHARMACY_FORWARD")

    # Minimal prescription shell for dispense queue
    rx = Prescription(
        encounter_id=enc.id,
        patient_id=enc.patient_id,
        prescribed_by=staff.id,
        status="ACTIVE",
    )
    # Some schemas use prescription_id string — set if column exists
    if hasattr(Prescription, "prescription_id"):
        setattr(rx, "prescription_id", f"RX-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{str(uuid4())[:6].upper()}")
    db.add(rx)
    db.flush()
    item_kwargs = {"prescription_id": rx.id, "medication_id": med.id}
    # quantity / dose fields vary — set safe defaults if present
    if hasattr(PrescriptionItem, "quantity"):
        item_kwargs["quantity"] = 1
    if hasattr(PrescriptionItem, "dose"):
        item_kwargs["dose"] = row.description[:80] if row.description else "As directed"
    if hasattr(PrescriptionItem, "instructions"):
        item_kwargs["instructions"] = row.notes or "From clinical order"
    try:
        db.add(PrescriptionItem(**item_kwargs))
    except Exception:
        # Fallback: prescription header only
        pass

    note = f"[FORWARDED:PHARMACY] linked_prescription={rx.id} medication={getattr(med, 'name', med.id)}"
    row.notes = f"{row.notes}\n{note}".strip() if row.notes else note
    if actor_user_id:
        record_audit(
            db,
            action="PRESCRIPTION_CREATED",
            resource_type="PRESCRIPTION",
            resource_id=str(rx.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=enc.facility_id,
            patient_id=enc.patient_id,
            metadata={"from_clinical_order": str(row.id)},
            commit=False,
        )
    return {
        "department": "PHARMACY",
        "linked_id": str(rx.id),
        "medication": getattr(med, "name", None),
        "matched": True,
        "message": f"Prescription created for {getattr(med, 'name', med.id)}",
    }
