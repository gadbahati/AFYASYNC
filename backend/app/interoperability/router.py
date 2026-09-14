from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.interoperability.schemas import FHIRCapabilityResponse, FHIRPatientResource
from app.interoperability.service import get_fhir_patient
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/interoperability", tags=["Interoperability"])
PERMISSION = "interoperability.patient.read"


@router.get("/metadata", response_model=FHIRCapabilityResponse)
def metadata(user: User = Depends(require_permission(PERMISSION))) -> FHIRCapabilityResponse:
    return FHIRCapabilityResponse()


@router.get("/Patient/{patient_id}", response_model=FHIRPatientResource)
def read_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(PERMISSION)),
) -> FHIRPatientResource:
    try:
        return get_fhir_patient(db, patient_id=patient_id, facility_id=facility_id, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        status_code = 403 if code == "PATIENT_NOT_IN_FACILITY" else 404
        raise HTTPException(status_code=status_code, detail=code) from exc
