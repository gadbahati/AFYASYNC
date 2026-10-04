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


def list_my_consents(db: Session, person_id: UUID) -> list[SensitiveDiseaseConsent]:
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
    """Patient changes a disclosure decision — new signature required every time."""
    consent = db.get(SensitiveDiseaseConsent, consent_id)
    if consent is None or consent.patient_id != person_id:
        raise PortalError("CONSENT_NOT_FOUND")

    sig = (payload.signature_data or "").strip()
    if len(sig) < 2:
        raise PortalError("SIGNATURE_REQUIRED")

    consent.consent_given = payload.consent_given
    consent.share_scope = "CROSS_FACILITY" if payload.consent_given else "FACILITY_ONLY"
    consent.signature_data = sig[:8000]
    consent.signature_method = (payload.signature_method or "TYPED_NAME")[:50]
    if payload.notes is not None:
        consent.notes = payload.notes[:2000] if payload.notes else None

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
    try:
        from app.coverage.models import Coverage

        return list(
            db.scalars(
                select(Coverage)
                .where(Coverage.person_id == person_id)
                .order_by(Coverage.created_at.desc())
            )
        )
    except Exception:
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


def get_my_results(db: Session, person_id: UUID, *, limit: int = 50) -> tuple[list, list]:
    """Return only finalized patient-owned laboratory and radiology results."""
    limit = min(max(limit, 1), 100)
    labs = []
    imaging = []

    from app.laboratory.models import LabOrder, LabOrderItem, LabResult, LabTest

    lab_rows = db.execute(
        select(LabResult, LabOrderItem, LabOrder, LabTest)
        .join(LabOrderItem, LabOrderItem.id == LabResult.lab_order_item_id)
        .join(LabOrder, LabOrder.id == LabOrderItem.lab_order_id)
        .join(LabTest, LabTest.id == LabOrderItem.test_id)
        .where(
            LabOrder.patient_id == person_id,
            LabResult.verified_by.is_not(None),
        )
        .order_by(LabResult.created_at.desc(), LabResult.id.desc())
        .limit(limit)
    ).all()

    for result, item, order, test in lab_rows:
        labs.append(
            {
                "id": result.id,
                "lab_order_item_id": item.id,
                "order_id": order.order_id,
                "encounter_id": order.encounter_id,
                "test_name": test.name,
                "test_code": test.code,
                "result": result.result,
                "unit": result.unit,
                "reference_range": result.reference_range,
                "comments": result.comments,
                "status": result.status,
                "verified_at": result.verified_at,
                "created_at": result.created_at,
            }
        )

    from app.radiology.models import ImagingOrder, ImagingReport, ImagingTest

    imaging_rows = db.execute(
        select(ImagingReport, ImagingOrder, ImagingTest)
        .join(ImagingOrder, ImagingOrder.id == ImagingReport.order_id)
        .join(ImagingTest, ImagingTest.id == ImagingOrder.test_id)
        .where(
            ImagingOrder.patient_id == person_id,
            ImagingReport.report_status.in_(["FINAL", "REVIEWED"]),
        )
        .order_by(ImagingReport.reported_at.desc(), ImagingReport.id.desc())
        .limit(limit)
    ).all()

    for report, order, test in imaging_rows:
        imaging.append(
            {
                "id": report.id,
                "order_id": order.id,
                "order_number": order.order_number,
                "encounter_id": order.encounter_id,
                "test_name": test.name,
                "modality": test.modality,
                "findings": report.findings,
                "impression": report.impression,
                "report_status": report.report_status,
                "reported_at": report.reported_at,
                "reviewed_at": report.reviewed_at,
            }
        )

    return labs, imaging
