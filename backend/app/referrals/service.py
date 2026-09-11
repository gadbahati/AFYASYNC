from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.encounters.models import Encounter
from app.facilities.models import Department, Facility
from app.notifications.events import notify_patient_event
from app.rbac.models import Staff
from app.referrals.models import Referral, Transfer


class ReferralError(ValueError):
    pass


REFERRAL_TRANSITIONS = {
    "CREATED": {"SENT", "CANCELLED"},
    "SENT": {"ACCEPTED", "DECLINED", "CANCELLED"},
    "ACCEPTED": {"IN_PROGRESS", "CANCELLED"},
    "IN_PROGRESS": {"COMPLETED", "CANCELLED"},
    "COMPLETED": set(),
    "DECLINED": set(),
    "CANCELLED": set(),
}

TRANSFER_TRANSITIONS = {
    "REQUESTED": {"ACCEPTED", "CANCELLED"},
    "ACCEPTED": {"IN_TRANSIT", "CANCELLED"},
    "IN_TRANSIT": {"ARRIVED", "CANCELLED"},
    "ARRIVED": set(),
    "CANCELLED": set(),
}


def _encounter(db: Session, encounter_id: UUID, facility_id: UUID) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise ReferralError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise ReferralError("FACILITY_ACCESS_DENIED")
    if encounter.status != "OPEN":
        raise ReferralError("ENCOUNTER_NOT_OPEN")
    return encounter


def _staff(db: Session, staff_id: UUID, facility_id: UUID) -> Staff:
    staff = db.get(Staff, staff_id)
    if staff is None or staff.facility_id != facility_id or staff.status != "ACTIVE":
        raise ReferralError("STAFF_NOT_FOUND")
    return staff


def create_referral(db: Session, facility_id: UUID, staff_id: UUID, payload: dict, *, actor_user_id: UUID | None = None) -> Referral:
    encounter = _encounter(db, payload["encounter_id"], facility_id)
    _staff(db, staff_id, facility_id)
    destination = db.get(Facility, payload["destination_facility_id"])
    if destination is None or destination.status != "ACTIVE":
        raise ReferralError("DESTINATION_FACILITY_NOT_FOUND")
    if destination.id == facility_id:
        raise ReferralError("DESTINATION_MUST_DIFFER")
    department_id = payload.get("destination_department_id")
    if department_id is not None:
        department = db.get(Department, department_id)
        if department is None or department.facility_id != destination.id:
            raise ReferralError("DESTINATION_DEPARTMENT_NOT_FOUND")

    referral = Referral(
        referral_id=f"REF-{uuid4().hex[:20].upper()}",
        patient_id=encounter.patient_id,
        encounter_id=encounter.id,
        source_facility_id=facility_id,
        destination_facility_id=destination.id,
        destination_department_id=department_id,
        referred_by=staff_id,
        reason=payload["reason"],
        priority=payload.get("priority", "ROUTINE"),
        clinical_summary=payload.get("clinical_summary"),
        status="CREATED",
    )
    db.add(referral)
    notify_patient_event(
        db,
        patient_id=referral.patient_id,
        event_type="REFERRAL_CREATED",
        facility_id=facility_id,
        metadata={"status": referral.status},
        actor_user_id=actor_user_id,
        commit=False,
    )
    db.commit()
    db.refresh(referral)
    record_audit(db, action="CREATE_REFERRAL", resource_type="REFERRAL", resource_id=str(referral.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=referral.patient_id, metadata={"referral_id": referral.referral_id, "destination_facility_id": str(destination.id)})
    return referral


def update_referral_status(db: Session, facility_id: UUID, referral_id: UUID, new_status: str, *, actor_user_id: UUID | None = None) -> Referral:
    referral = db.get(Referral, referral_id)
    if referral is None:
        raise ReferralError("REFERRAL_NOT_FOUND")
    if facility_id not in {referral.source_facility_id, referral.destination_facility_id}:
        raise ReferralError("FACILITY_ACCESS_DENIED")
    if new_status not in REFERRAL_TRANSITIONS.get(referral.status, set()):
        raise ReferralError("INVALID_REFERRAL_TRANSITION")
    referral.status = new_status
    notify_patient_event(
        db,
        patient_id=referral.patient_id,
        event_type="REFERRAL_STATUS_CHANGED",
        facility_id=facility_id,
        metadata={"status": new_status},
        actor_user_id=actor_user_id,
        commit=False,
    )
    db.commit()
    db.refresh(referral)
    record_audit(db, action="UPDATE_REFERRAL_STATUS", resource_type="REFERRAL", resource_id=str(referral.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=referral.patient_id, metadata={"status": new_status})
    return referral


def create_transfer(db: Session, facility_id: UUID, staff_id: UUID, payload: dict, *, actor_user_id: UUID | None = None) -> Transfer:
    encounter = _encounter(db, payload["encounter_id"], facility_id)
    _staff(db, staff_id, facility_id)
    destination = db.get(Facility, payload["destination_facility_id"])
    if destination is None or destination.status != "ACTIVE":
        raise ReferralError("DESTINATION_FACILITY_NOT_FOUND")
    if destination.id == facility_id:
        raise ReferralError("DESTINATION_MUST_DIFFER")

    referral_id = payload.get("referral_id")
    if referral_id is not None:
        referral = db.get(Referral, referral_id)
        if referral is None or referral.patient_id != encounter.patient_id or referral.source_facility_id != facility_id or referral.destination_facility_id != destination.id:
            raise ReferralError("INVALID_REFERRAL")
        if referral.status not in {"ACCEPTED", "IN_PROGRESS"}:
            raise ReferralError("REFERRAL_NOT_READY_FOR_TRANSFER")

    transfer = Transfer(
        transfer_id=f"TRF-{uuid4().hex[:20].upper()}",
        referral_id=referral_id,
        patient_id=encounter.patient_id,
        encounter_id=encounter.id,
        source_facility_id=facility_id,
        destination_facility_id=destination.id,
        requested_by=staff_id,
        reason=payload["reason"],
        notes=payload.get("notes"),
        status="REQUESTED",
    )
    db.add(transfer)
    notify_patient_event(
        db,
        patient_id=transfer.patient_id,
        event_type="TRANSFER_REQUESTED",
        facility_id=facility_id,
        metadata={"status": transfer.status},
        actor_user_id=actor_user_id,
        commit=False,
    )
    db.commit()
    db.refresh(transfer)
    record_audit(db, action="CREATE_TRANSFER", resource_type="TRANSFER", resource_id=str(transfer.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=transfer.patient_id, metadata={"transfer_id": transfer.transfer_id, "destination_facility_id": str(destination.id)})
    return transfer


def update_transfer_status(db: Session, facility_id: UUID, transfer_id: UUID, new_status: str, *, actor_user_id: UUID | None = None) -> Transfer:
    transfer = db.get(Transfer, transfer_id)
    if transfer is None:
        raise ReferralError("TRANSFER_NOT_FOUND")
    if facility_id not in {transfer.source_facility_id, transfer.destination_facility_id}:
        raise ReferralError("FACILITY_ACCESS_DENIED")
    if new_status not in TRANSFER_TRANSITIONS.get(transfer.status, set()):
        raise ReferralError("INVALID_TRANSFER_TRANSITION")
    transfer.status = new_status
    notify_patient_event(
        db,
        patient_id=transfer.patient_id,
        event_type="TRANSFER_STATUS_CHANGED",
        facility_id=facility_id,
        metadata={"status": new_status},
        actor_user_id=actor_user_id,
        commit=False,
    )
    db.commit()
    db.refresh(transfer)
    record_audit(db, action="UPDATE_TRANSFER_STATUS", resource_type="TRANSFER", resource_id=str(transfer.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=transfer.patient_id, metadata={"status": new_status})
    return transfer
