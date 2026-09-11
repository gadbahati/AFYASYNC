from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.patients.models import AfyaIdentity, PatientFacility, Person
from app.patients.schemas import PatientCreate, PatientUpdate


_ALLOWED_PATIENT_STATUSES = {"ACTIVE", "INACTIVE"}


def _next_afya_id(db: Session) -> str:
    """Generate the next concurrency-safe human-facing AfyaSync ID."""
    sequence = db.scalar(text("nextval('afasync_patient_id_seq')"))
    if sequence is None:
        raise RuntimeError("IDENTITY_SEQUENCE_UNAVAILABLE")
    return f"AF-{int(sequence):08d}"


def create_patient(db: Session, payload: PatientCreate, *, actor_user_id: UUID | None = None, facility_id: UUID | None = None) -> Person:
    if facility_id is None:
        raise ValueError("FACILITY_CONTEXT_REQUIRED")
    if payload.phone:
        existing = db.scalar(select(Person).where(Person.phone == payload.phone, Person.first_name.ilike(payload.first_name), Person.last_name.ilike(payload.last_name)))
        if existing:
            raise ValueError("DUPLICATE_PATIENT")
    person = Person(**payload.model_dump())
    db.add(person)
    db.flush()
    identity = AfyaIdentity(person_id=person.id, afya_id=_next_afya_id(db))
    db.add(identity)
    db.flush()
    db.add(PatientFacility(patient_id=person.id, facility_id=facility_id, status="ACTIVE"))
    db.flush()
    record_audit(db, action="CREATE_PATIENT", resource_type="PERSON", resource_id=str(person.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=person.id, metadata={"afya_id": identity.afya_id}, commit=False)
    db.commit()
    db.refresh(person)
    return person


def get_patient_for_facility(db: Session, patient_id: UUID, facility_id: UUID) -> Person | None:
    statement = select(Person).join(PatientFacility, PatientFacility.patient_id == Person.id).where(Person.id == patient_id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE")
    return db.scalar(statement)


def update_patient(db: Session, patient: Person, payload: PatientUpdate, *, actor_user_id: UUID | None = None, facility_id: UUID | None = None) -> Person:
    if facility_id is None:
        raise ValueError("FACILITY_CONTEXT_REQUIRED")
    membership = db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id == patient.id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE"))
    if membership is None:
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise ValueError("NO_CHANGES")
    if "status" in changes and changes["status"] not in _ALLOWED_PATIENT_STATUSES:
        raise ValueError("INVALID_PATIENT_STATUS")
    if "phone" in changes and changes["phone"]:
        duplicate = db.scalar(select(Person).where(Person.id != patient.id, Person.phone == changes["phone"]))
        if duplicate:
            raise ValueError("DUPLICATE_PHONE")
    changed_fields = sorted(changes)
    for field, value in changes.items():
        setattr(patient, field, value)
    db.flush()
    record_audit(db, action="UPDATE_PATIENT", resource_type="PERSON", resource_id=str(patient.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=patient.id, metadata={"changed_fields": changed_fields}, commit=False)
    db.commit()
    db.refresh(patient)
    return patient


def search_patients(db: Session, query: str, facility_id: UUID, limit: int = 20) -> list[tuple[Person, AfyaIdentity]]:
    term = f"%{query.strip()}%"
    statement = select(Person, AfyaIdentity).join(AfyaIdentity, AfyaIdentity.person_id == Person.id).join(PatientFacility, PatientFacility.patient_id == Person.id).where(PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE", or_(AfyaIdentity.afya_id.ilike(term), Person.phone.ilike(term), Person.first_name.ilike(term), Person.last_name.ilike(term))).order_by(Person.last_name, Person.first_name).limit(min(max(limit, 1), 50))
    return list(db.execute(statement).all())
