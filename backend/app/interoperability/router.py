from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.interoperability.clinical_schemas import FHIRBundleResource
from app.interoperability.schemas import FHIRCapabilityResponse, FHIRPatientResource
from app.interoperability.service import get_fhir_patient
from app.interoperability.clinical_service import get_fhir_clinical_bundle
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/interoperability", tags=["Interoperability"])
PATIENT_PERMISSION = "interoperability.patient.read"
CLINICAL_PERMISSION = "interoperability.clinical.read"


@router.get("/metadata", response_model=FHIRCapabilityResponse)
def metadata(user: User = Depends(require_permission(PATIENT_PERMISSION))) -> FHIRCapabilityResponse:
    return FHIRCapabilityResponse()


@router.get("/Patient/{patient_id}", response_model=FHIRPatientResource)
def read_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(PATIENT_PERMISSION)),
) -> FHIRPatientResource:
    try:
        return get_fhir_patient(db, patient_id=patient_id, facility_id=facility_id, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        status_code = 403 if code == "PATIENT_NOT_IN_FACILITY" else 404
        raise HTTPException(status_code=status_code, detail=code) from exc


@router.get("/Patient/{patient_id}/$summary", response_model=FHIRBundleResource)
def read_clinical_summary(
    patient_id: UUID,
    access_reason: str = Query(min_length=3, max_length=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLINICAL_PERMISSION)),
) -> FHIRBundleResource:
    try:
        return get_fhir_clinical_bundle(
            db,
            patient_id=patient_id,
            facility_id=facility_id,
            actor_user_id=user.id,
            access_reason=access_reason,
        )
    except ValueError as exc:
        code = str(exc)
        status_code = 403 if code == "PATIENT_NOT_IN_FACILITY" else 404 if code in {"PATIENT_NOT_FOUND", "IDENTITY_NOT_ACTIVE"} else 422
        raise HTTPException(status_code=status_code, detail=code) from exc
