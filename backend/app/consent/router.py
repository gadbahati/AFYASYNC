"""API routes for patient-controlled sensitive disease disclosure."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_facility_context
from app.consent.schemas import (
    ConsentCheckResult,
    SensitiveDiseaseConsentCreate,
    SensitiveDiseaseConsentOut,
)
from app.consent.service import (
    check_diagnosis_may_be_shared,
    list_patient_consents,
    record_sensitive_consent,
)
from app.database import get_db

router = APIRouter(prefix="/api/v1/consent", tags=["consent"])


@router.post(
    "/sensitive-disease",
    response_model=SensitiveDiseaseConsentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_sensitive_disease_consent(
    payload: SensitiveDiseaseConsentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    """Record patient digital consent for a sensitive diagnosis.

    The patient must explicitly sign (or otherwise confirm) on screen.
    Only when consent_given=True will the diagnosis be visible at other facilities.
    """
    if payload.facility_id != facility_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="facility_id must match the current facility context",
        )

    try:
        consent = record_sensitive_consent(
            db,
            payload=payload,
            recorded_by=current_user.id,
            ip_address=request.client.host if request.client else None,
        )
        db.commit()
        db.refresh(consent)
        return consent
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "/sensitive-disease/check/{diagnosis_id}",
    response_model=ConsentCheckResult,
)
def check_sensitive_diagnosis_share(
    diagnosis_id: UUID,
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Check whether a diagnosis may be shown in a cross-facility view."""
    return check_diagnosis_may_be_shared(
        db, diagnosis_id=diagnosis_id, patient_id=patient_id
    )


@router.get(
    "/sensitive-disease/patient/{patient_id}",
    response_model=list[SensitiveDiseaseConsentOut],
)
def get_patient_sensitive_consents(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    """List consent decisions recorded for a patient at the current facility."""
    return list_patient_consents(db, patient_id=patient_id, facility_id=facility_id)
