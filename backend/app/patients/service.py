from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
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


def get_patient_facility_enrollments(db: Session, patient_id: UUID, facility_id: UUID) -> list[PatientFacility]:
    statement = select(PatientFacility).where(PatientFacility.patient_id == patient_id, PatientFacility.facility_id == facility_id).order_by(PatientFacility.created_at)
    return list(db.scalars(statement).all())


def list_patients_for_facility(
    db: Session,
    facility_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
    enrollment_status: str | None = "ACTIVE",
) -> tuple[list[tuple[Person, AfyaIdentity]], int]:
    """Return patients enrolled at the given facility only, plus total count.

    Strictly facility-scoped: never returns patients that are only enrolled
    at other facilities. Defaults to ACTIVE enrollments.
    """
    if facility_id is None:
        raise ValueError("FACILITY_CONTEXT_REQUIRED")
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)

    base_filters = [PatientFacility.facility_id == facility_id]
    if enrollment_status is not None:
        if enrollment_status not in _ALLOWED_PATIENT_STATUSES:
            raise ValueError("INVALID_ENROLLMENT_STATUS")
        base_filters.append(PatientFacility.status == enrollment_status)

    count_stmt = (
        select(func.count())
        .select_from(PatientFacility)
        .where(*base_filters)
    )
    total = int(db.scalar(count_stmt) or 0)

    statement = (
        select(Person, AfyaIdentity)
        .join(AfyaIdentity, AfyaIdentity.person_id == Person.id)
        .join(PatientFacility, PatientFacility.patient_id == Person.id)
        .where(*base_filters)
        .order_by(Person.last_name, Person.first_name, Person.id)
        .offset(offset)
        .limit(limit)
    )

    items = list(db.execute(statement).all())
    return items, total


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


def enroll_patient_in_facility(db: Session, patient_id: UUID, facility_id: UUID, *, actor_user_id: UUID | None = None) -> PatientFacility:
    if facility_id is None:
        raise ValueError("FACILITY_CONTEXT_REQUIRED")
    patient_exists = db.scalar(select(AfyaIdentity.person_id).where(AfyaIdentity.person_id == patient_id))
    if patient_exists is None:
        raise ValueError("PATIENT_NOT_FOUND")
    membership = db.scalar(select(PatientFacility).where(PatientFacility.patient_id == patient_id, PatientFacility.facility_id == facility_id))
    if membership is not None:
        if membership.status == "ACTIVE":
            raise ValueError("PATIENT_ALREADY_ENROLLED")
        membership.status = "ACTIVE"
        db.flush()
        record_audit(db, action="REACTIVATE_PATIENT_FACILITY", resource_type="PATIENT_FACILITY", resource_id=str(membership.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=patient_id, commit=False)
        db.commit()
        db.refresh(membership)
        return membership
    membership = PatientFacility(patient_id=patient_id, facility_id=facility_id, status="ACTIVE")
    db.add(membership)
    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        # The unique patient/facility constraint may race with another request.
        # A savepoint keeps the caller's outer transaction usable after the
        # losing insert is rolled back. Re-read the row and apply the same
        # business rules as the non-racing path.
        membership = db.scalar(select(PatientFacility).where(PatientFacility.patient_id == patient_id, PatientFacility.facility_id == facility_id))
        if membership is None:
            raise
        if membership.status == "ACTIVE":
            raise ValueError("PATIENT_ALREADY_ENROLLED")
        membership.status = "ACTIVE"
        db.flush()
        record_audit(db, action="REACTIVATE_PATIENT_FACILITY", resource_type="PATIENT_FACILITY", resource_id=str(membership.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=patient_id, commit=False)
        db.commit()
        db.refresh(membership)
        return membership
    record_audit(db, action="ENROLL_PATIENT_FACILITY", resource_type="PATIENT_FACILITY", resource_id=str(membership.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=patient_id, commit=False)
    db.commit()
    db.refresh(membership)
    return membership


def update_patient_facility_status(db: Session, patient_id: UUID, facility_id: UUID, status: str, *, actor_user_id: UUID | None = None) -> PatientFacility:
    if facility_id is None:
        raise ValueError("FACILITY_CONTEXT_REQUIRED")
    if status not in _ALLOWED_PATIENT_STATUSES:
        raise ValueError("INVALID_PATIENT_FACILITY_STATUS")
    membership = db.scalar(select(PatientFacility).where(PatientFacility.patient_id == patient_id, PatientFacility.facility_id == facility_id))
    if membership is None:
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    if membership.status == status:
        raise ValueError("PATIENT_FACILITY_STATUS_UNCHANGED")
    previous_status = membership.status
    membership.status = status
    db.flush()
    record_audit(db, action="UPDATE_PATIENT_FACILITY_STATUS", resource_type="PATIENT_FACILITY", resource_id=str(membership.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=patient_id, metadata={"previous_status": previous_status, "new_status": status}, commit=False)
    db.commit()
    db.refresh(membership)
    return membership


def search_patients(db: Session, query: str, facility_id: UUID, limit: int = 20) -> list[tuple[Person, AfyaIdentity]]:
    term = f"%{query.strip()}%"
    statement = select(Person, AfyaIdentity).join(AfyaIdentity, AfyaIdentity.person_id == Person.id).join(PatientFacility, PatientFacility.patient_id == Person.id).where(PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE", or_(AfyaIdentity.afya_id.ilike(term), Person.phone.ilike(term), Person.first_name.ilike(term), Person.last_name.ilike(term))).order_by(Person.last_name, Person.first_name).limit(min(max(limit, 1), 50))
    return list(db.execute(statement).all())