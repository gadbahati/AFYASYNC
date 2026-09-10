from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.patients.models import AfyaIdentity, Person
from app.patients.schemas import PatientCreate


def _next_afya_id(db: Session) -> str:
    """Generate the next concurrency-safe human-facing AfyaSync ID."""
    sequence = db.scalar(text("nextval('afasync_patient_id_seq')"))
    if sequence is None:
        raise RuntimeError("IDENTITY_SEQUENCE_UNAVAILABLE")
    return f"AF-{int(sequence):08d}"


def create_patient(db: Session, payload: PatientCreate) -> Person:
    # Conservative duplicate candidate search. A final identity should be
    # confirmed through an authorised workflow before merging records.
    if payload.phone:
        existing = db.scalar(
            select(Person).where(
                Person.phone == payload.phone,
                Person.first_name.ilike(payload.first_name),
                Person.last_name.ilike(payload.last_name),
            )
        )
        if existing:
            raise ValueError("DUPLICATE_PATIENT")

    person = Person(**payload.model_dump())
    db.add(person)
    db.flush()

    identity = AfyaIdentity(person_id=person.id, afya_id=_next_afya_id(db))
    db.add(identity)
    db.commit()
    db.refresh(person)
    return person


def search_patients(db: Session, query: str, limit: int = 20) -> list[tuple[Person, AfyaIdentity]]:
    term = f"%{query.strip()}%"
    statement = (
        select(Person, AfyaIdentity)
        .join(AfyaIdentity, AfyaIdentity.person_id == Person.id)
        .where(
            or_(
                AfyaIdentity.afya_id.ilike(term),
                Person.phone.ilike(term),
                Person.first_name.ilike(term),
                Person.last_name.ilike(term),
            )
        )
        .order_by(Person.last_name, Person.first_name)
        .limit(min(max(limit, 1), 50))
    )
    return list(db.execute(statement).all())
