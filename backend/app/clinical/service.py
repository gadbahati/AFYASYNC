from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clinical.models import Consultation, Diagnosis, Vital
from app.encounters.models import Encounter
from app.rbac.models import Staff


def _open_encounter(db: Session, encounter_id: UUID) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    if encounter.status != "OPEN":
        raise ValueError("ENCOUNTER_CLOSED")
    return encounter


def _staff_at_facility(db: Session, staff_id: UUID, facility_id: UUID) -> Staff:
    staff = db.get(Staff, staff_id)
    if staff is None or staff.facility_id != facility_id or staff.status != "ACTIVE":
        raise ValueError("STAFF_NOT_FOUND")
    return staff


def _calculate_bmi(weight_kg: float | None, height_cm: float | None) -> float | None:
    if not weight_kg or not height_cm:
        return None
    height_m = height_cm / 100
    if height_m <= 0:
        return None
    return round(weight_kg / (height_m * height_m), 2)


def record_vitals(db: Session, encounter_id: UUID, staff_id: UUID, data: dict) -> Vital:
    encounter = _open_encounter(db, encounter_id)
    _staff_at_facility(db, staff_id, encounter.facility_id)
    vital = Vital(
        encounter_id=encounter_id,
        recorded_by=staff_id,
        bmi=_calculate_bmi(data.get("weight_kg"), data.get("height_cm")),
        **data,
    )
    db.add(vital)
    db.commit()
    db.refresh(vital)
    return vital


def create_or_update_consultation(db: Session, encounter_id: UUID, doctor_id: UUID, data: dict) -> Consultation:
    encounter = _open_encounter(db, encounter_id)
    _staff_at_facility(db, doctor_id, encounter.facility_id)
    consultation = db.scalar(select(Consultation).where(Consultation.encounter_id == encounter_id))
    if consultation is None:
        consultation = Consultation(encounter_id=encounter_id, doctor_id=doctor_id, **data)
        db.add(consultation)
    else:
        consultation.doctor_id = doctor_id
        for key, value in data.items():
            setattr(consultation, key, value)
    db.commit()
    db.refresh(consultation)
    return consultation


def add_diagnosis(db: Session, encounter_id: UUID, staff_id: UUID, data: dict) -> Diagnosis:
    encounter = _open_encounter(db, encounter_id)
    _staff_at_facility(db, staff_id, encounter.facility_id)
    diagnosis = Diagnosis(encounter_id=encounter_id, recorded_by=staff_id, **data)
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)
    return diagnosis
