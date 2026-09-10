from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.encounters.models import Encounter
from app.facilities.models import Department, Facility
from app.patients.models import Person


def _require_active_context(db: Session, patient_id: UUID, facility_id: UUID, department_id: UUID) -> None:
    patient = db.get(Person, patient_id)
    facility = db.get(Facility, facility_id)
    department = db.get(Department, department_id)
    if patient is None or patient.status != "ACTIVE":
        raise ValueError("PATIENT_NOT_FOUND")
    if facility is None or facility.status != "ACTIVE":
        raise ValueError("FACILITY_NOT_FOUND")
    if department is None or department.facility_id != facility_id or department.status != "ACTIVE":
        raise ValueError("DEPARTMENT_NOT_FOUND")


def _next_encounter_id(db: Session) -> str:
    number = db.scalar(text("SELECT nextval('afasync_encounter_seq')"))
    if number is None:
        raise RuntimeError("ENCOUNTER_SEQUENCE_UNAVAILABLE")
    return f"ENC-{datetime.now(timezone.utc):%Y%m%d}-{int(number):05d}"


def create_encounter(db: Session, data: dict, created_by: UUID, commit: bool = True) -> Encounter:
    _require_active_context(db, data["patient_id"], data["facility_id"], data["department_id"])
    encounter = Encounter(encounter_id=_next_encounter_id(db), created_by=created_by, **data)
    db.add(encounter)
    db.flush()
    if commit:
        db.commit()
        db.refresh(encounter)
    return encounter


def get_encounter(db: Session, encounter_id: UUID) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    return encounter


def close_encounter(db: Session, encounter_id: UUID) -> Encounter:
    encounter = get_encounter(db, encounter_id)
    if encounter.status != "OPEN":
        raise ValueError("ENCOUNTER_CLOSED")
    encounter.status = "COMPLETED"
    encounter.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(encounter)
    return encounter
