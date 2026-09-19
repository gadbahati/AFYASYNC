"""Service layer for patient-controlled sensitive disease disclosure."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.consent.models import SensitiveDiseaseConsent
from app.consent.schemas import ConsentCheckResult, SensitiveDiseaseConsentCreate


def record_sensitive_consent(
    db: Session,
    *,
    payload: SensitiveDiseaseConsentCreate,
    recorded_by: UUID,
    ip_address: str | None = None,
) -> SensitiveDiseaseConsent:
    """Record the patient's explicit consent decision for a sensitive diagnosis.

    - consent_given=True  → share_scope becomes CROSS_FACILITY
    - consent_given=False → share_scope remains FACILITY_ONLY
    """
    # Prevent double consent records for the same diagnosis
    existing = db.scalar(
        select(SensitiveDiseaseConsent).where(
            SensitiveDiseaseConsent.diagnosis_id == payload.diagnosis_id
        )
    )
    if existing:
        raise ValueError("Consent has already been recorded for this diagnosis")

    share_scope = "CROSS_FACILITY" if payload.consent_given else "FACILITY_ONLY"

    consent = SensitiveDiseaseConsent(
        patient_id=payload.patient_id,
        diagnosis_id=payload.diagnosis_id,
        facility_id=payload.facility_id,
        encounter_id=payload.encounter_id,
        consent_given=payload.consent_given,
        share_scope=share_scope,
        sensitive_category_id=payload.sensitive_category_id,
        signature_data=payload.signature_data,
        signature_method=payload.signature_method,
        recorded_by=recorded_by,
        device_id=payload.device_id,
        ip_address=ip_address,
        notes=payload.notes,
    )
    db.add(consent)
    db.flush()

    record_audit(
        db,
        user_id=recorded_by,
        facility_id=payload.facility_id,
        patient_id=payload.patient_id,
        action="SENSITIVE_DISEASE_CONSENT_RECORDED",
        resource_type="SensitiveDiseaseConsent",
        resource_id=str(consent.id),
        result="SUCCESS",
        ip_address=ip_address,
        device_id=payload.device_id,
        metadata={
            "diagnosis_id": str(payload.diagnosis_id),
            "consent_given": payload.consent_given,
            "share_scope": share_scope,
            "signature_method": payload.signature_method,
        },
        commit=False,
    )

    return consent


def check_diagnosis_may_be_shared(
    db: Session,
    *,
    diagnosis_id: UUID,
    patient_id: UUID,
) -> ConsentCheckResult:
    """Determine whether a diagnosis is allowed to appear in cross-facility views.

    If no consent record exists, default to NOT shareable (safe default).
    """
    consent = db.scalar(
        select(SensitiveDiseaseConsent).where(
            SensitiveDiseaseConsent.diagnosis_id == diagnosis_id,
            SensitiveDiseaseConsent.patient_id == patient_id,
        )
    )

    if consent is None:
        return ConsentCheckResult(
            diagnosis_id=diagnosis_id,
            patient_id=patient_id,
            may_share_across_facilities=False,
            consent_given=None,
            share_scope=None,
            reason="No consent record found — defaulting to facility-only",
        )

    may_share = consent.consent_given and consent.share_scope == "CROSS_FACILITY"

    return ConsentCheckResult(
        diagnosis_id=diagnosis_id,
        patient_id=patient_id,
        may_share_across_facilities=may_share,
        consent_given=consent.consent_given,
        share_scope=consent.share_scope,
        reason=(
            "Patient consented to cross-facility sharing"
            if may_share
            else "Patient declined cross-facility sharing or scope is facility-only"
        ),
    )


def list_patient_consents(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID | None = None,
) -> list[SensitiveDiseaseConsent]:
    """List consent decisions for a patient (optionally filtered by facility)."""
    stmt = select(SensitiveDiseaseConsent).where(
        SensitiveDiseaseConsent.patient_id == patient_id
    )
    if facility_id is not None:
        stmt = stmt.where(SensitiveDiseaseConsent.facility_id == facility_id)
    stmt = stmt.order_by(SensitiveDiseaseConsent.consented_at.desc())
    return list(db.scalars(stmt).all())
