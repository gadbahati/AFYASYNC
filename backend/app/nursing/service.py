from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.nursing.models import NursingHandover, NursingNote, NursingObservation
from app.patients.models import PatientFacility


def _patient_ok(db: Session, patient_id: UUID, facility_id: UUID) -> bool:
    return db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id == patient_id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE")) is not None


def create_observation(db: Session, payload, facility_id: UUID, actor_user_id: UUID):
    if not _patient_ok(db, payload.patient_id, facility_id):
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    item = NursingObservation(recorded_by=actor_user_id, facility_id=facility_id, **payload.model_dump())
    db.add(item)
    record_audit(db, action="NURSING_OBSERVATION_RECORDED", resource_type="NursingObservation", result="SUCCESS", user_id=actor_user_id, resource_id=str(item.id), facility_id=facility_id, patient_id=payload.patient_id, commit=False)
    db.commit(); db.refresh(item)
    return item


def create_note(db: Session, payload, facility_id: UUID, actor_user_id: UUID):
    if not _patient_ok(db, payload.patient_id, facility_id):
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    item = NursingNote(author_id=actor_user_id, facility_id=facility_id, **payload.model_dump())
    db.add(item)
    record_audit(db, action="NURSING_NOTE_CREATED", resource_type="NursingNote", result="SUCCESS", user_id=actor_user_id, resource_id=str(item.id), facility_id=facility_id, patient_id=payload.patient_id, commit=False)
    db.commit(); db.refresh(item)
    return item


def create_handover(db: Session, payload, facility_id: UUID, actor_user_id: UUID):
    if not _patient_ok(db, payload.patient_id, facility_id):
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    item = NursingHandover(handed_over_by=actor_user_id, facility_id=facility_id, **payload.model_dump())
    db.add(item)
    record_audit(db, action="NURSING_HANDOVER_CREATED", resource_type="NursingHandover", result="SUCCESS", user_id=actor_user_id, resource_id=str(item.id), facility_id=facility_id, patient_id=payload.patient_id, commit=False)
    db.commit(); db.refresh(item)
    return item
