from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import Consultation, Diagnosis, Vital
from app.consent.models import SensitiveDiseaseConsent
from app.encounters.models import Encounter
from app.laboratory.models import LabOrder
from app.patients.models import AfyaIdentity, Person
from app.pharmacy.models import Prescription
from app.portal.schemas import PortalConsentUpdate
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
    """Patient-safe clinical summary: only the authenticated patient's own encounter.

    Sensitive diagnoses are included because the patient is viewing their own record.
    """
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


def list_my_consents(db: Session, person_id: UUID) -> list[SensitiveDiseaseConsent]:
    """All sensitive disclosure decisions belonging to this patient."""
    return list(
        db.scalars(
            select(SensitiveDiseaseConsent)
            .where(SensitiveDiseaseConsent.patient_id == person_id)
            .order_by(SensitiveDiseaseConsent.consented_at.desc())
        )
    )


def update_my_consent(
    db: Session,
    *,
    person_id: UUID,
    consent_id: UUID,
    payload: PortalConsentUpdate,
    actor_user_id: UUID,
) -> SensitiveDiseaseConsent:
    """Allow the patient to change a previous disclosure decision (with new signature)."""
    consent = db.get(SensitiveDiseaseConsent, consent_id)
    if consent is None or consent.patient_id != person_id:
        raise PortalError("CONSENT_NOT_FOUND")

    consent.consent_given = payload.consent_given
    consent.share_scope = "CROSS_FACILITY" if payload.consent_given else "FACILITY_ONLY"
    if payload.signature_data is not None:
        consent.signature_data = payload.signature_data
    if payload.signature_method is not None:
        consent.signature_method = payload.signature_method
    if payload.notes is not None:
        consent.notes = payload.notes

    db.add(consent)
    db.flush()

    record_audit(
        db,
        action="PORTAL_CONSENT_UPDATED",
        resource_type="SensitiveDiseaseConsent",
        resource_id=str(consent.id),
        result="SUCCESS",
        user_id=actor_user_id,
        patient_id=person_id,
        facility_id=consent.facility_id,
        metadata={
            "consent_given": payload.consent_given,
            "share_scope": consent.share_scope,
        },
        commit=False,
    )
    return consent


def list_my_coverage(db: Session, person_id: UUID) -> list:
    """Return coverage rows linked to this patient (best-effort, non-breaking)."""
    try:
        from app.coverage.models import Coverage

        rows = list(
            db.scalars(
                select(Coverage)
                .where(Coverage.patient_id == person_id)
                .order_by(Coverage.created_at.desc())
            )
        )
        return rows
    except Exception:
        # Coverage model shape may vary; portal must not break if structure differs
        return []


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
