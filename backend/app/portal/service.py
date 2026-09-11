from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import Consultation, Diagnosis, Vital
from app.encounters.models import Encounter
from app.laboratory.models import LabOrder
from app.patients.models import AfyaIdentity, Person
from app.pharmacy.models import Prescription
from app.referrals.models import Referral


class PortalError(ValueError):
    pass


def require_patient_person_id(user_person_id: UUID | None) -> UUID:
    if user_person_id is None:
        raise PortalError("PATIENT_IDENTITY_REQUIRED")
    return user_person_id


def get_my_profile(db: Session, person_id: UUID) -> tuple[Person, AfyaIdentity | None]:
    person = db.get(Person, person_id)
    if person is None or person.status != "ACTIVE":
        raise PortalError("PATIENT_NOT_FOUND")
    identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person_id))
    return person, identity


def list_my_encounters(
    db: Session,
    person_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Encounter], int]:
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    filters = [Encounter.patient_id == person_id]
    total = int(db.scalar(select(func.count()).select_from(Encounter).where(*filters)) or 0)
    items = list(
        db.scalars(
            select(Encounter)
            .where(*filters)
            .order_by(Encounter.started_at.desc(), Encounter.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return items, total


def get_my_encounter(db: Session, person_id: UUID, encounter_id: UUID) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None or encounter.patient_id != person_id:
        raise PortalError("ENCOUNTER_NOT_FOUND")
    return encounter


def get_my_encounter_summary(db: Session, person_id: UUID, encounter_id: UUID) -> dict:
    """Patient-safe clinical summary: only the authenticated patient's own encounter."""
    encounter = get_my_encounter(db, person_id, encounter_id)

    vitals = list(
        db.scalars(
            select(Vital)
            .where(Vital.encounter_id == encounter_id)
            .order_by(Vital.recorded_at.asc(), Vital.id.asc())
        )
    )
    consultation = db.scalar(select(Consultation).where(Consultation.encounter_id == encounter_id))
    diagnoses = list(
        db.scalars(
            select(Diagnosis)
            .where(Diagnosis.encounter_id == encounter_id)
            .order_by(Diagnosis.created_at.asc(), Diagnosis.id.asc())
        )
    )
    lab_orders = list(
        db.scalars(
            select(LabOrder)
            .where(LabOrder.encounter_id == encounter_id)
            .order_by(LabOrder.created_at.asc(), LabOrder.id.asc())
        )
    )
    prescriptions = list(
        db.scalars(
            select(Prescription)
            .where(Prescription.encounter_id == encounter_id)
            .order_by(Prescription.created_at.asc(), Prescription.id.asc())
        )
    )
    return {
        "encounter": encounter,
        "vitals": vitals,
        "consultation": consultation,
        "diagnoses": diagnoses,
        "lab_orders": lab_orders,
        "prescriptions": prescriptions,
    }


def list_my_referrals(
    db: Session,
    person_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Referral], int]:
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    filters = [Referral.patient_id == person_id]
    total = int(db.scalar(select(func.count()).select_from(Referral).where(*filters)) or 0)
    items = list(
        db.scalars(
            select(Referral)
            .where(*filters)
            .order_by(Referral.created_at.desc(), Referral.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return items, total


def audit_portal_view(
    db: Session,
    *,
    user_id: UUID,
    person_id: UUID,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict | None = None,
) -> None:
    record_audit(
        db,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        result="SUCCESS",
        user_id=user_id,
        patient_id=person_id,
        metadata=metadata or {},
        commit=True,
    )
