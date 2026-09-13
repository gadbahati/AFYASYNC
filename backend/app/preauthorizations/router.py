from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.patients.models import PatientFacility
from app.preauthorizations.eligibility import EligibilityError, check_coverage_eligibility
from app.preauthorizations.eligibility_schemas import EligibilityCheckRequest, EligibilityCheckResponse
from app.preauthorizations.integration_service import PreAuthorizationIntegrationError, submit_preauthorization
from app.preauthorizations.schemas import PreAuthorizationCreate, PreAuthorizationDecision, PreAuthorizationResponse, PreAuthorizationSubmission, PreAuthorizationSubmissionResponse
from app.preauthorizations.service import PreAuthorizationError, decide_preauthorization, request_preauthorization

router = APIRouter(prefix="/api/v1/preauthorizations", tags=["Preauthorizations"])


def _error(exc: PreAuthorizationError | PreAuthorizationIntegrationError) -> HTTPException:
    code = str(exc)
    mapping = {
        "PATIENT_NOT_IN_FACILITY": 404, "COVERAGE_NOT_FOUND": 404, "PREAUTH_NOT_FOUND": 404,
        "ENCOUNTER_NOT_FOUND": 404, "FACILITY_ACCESS_DENIED": 403,
        "VERIFIED_COVERAGE_REQUIRED": 409, "COVERAGE_NOT_ACTIVE": 409, "COVERAGE_EXPIRED": 409,
        "PAYER_NOT_ACTIVE": 409, "BENEFIT_NOT_CONFIGURED": 409, "ENCOUNTER_NOT_OPEN": 409,
        "SHA_PAYER_REQUIRED": 400, "BENEFIT_PACKAGE_NOT_FOUND": 400, "INPATIENT_SHA_PACKAGE_REQUIRED": 400,
        "PREAUTH_NOT_DECIDABLE": 409, "PREAUTH_NOT_SUBMITTABLE": 409,
        "APPROVED_AMOUNT_EXCEEDS_REQUEST": 400, "REJECTED_AMOUNT_MUST_BE_ZERO": 400,
        "PREAUTHORIZATION_CREATE_FAILED": 409, "INTEGRATION_NOT_FOUND": 404,
        "INTEGRATION_NOT_ACTIVE": 409, "INVALID_PAYER_INTEGRATION": 409,
    }
    return HTTPException(status_code=mapping.get(code, 400), detail=code)


@router.post("/eligibility", response_model=EligibilityCheckResponse)
def check_eligibility(payload: EligibilityCheckRequest, db: Session = Depends(get_db), user: Any = Depends(require_permission("encounters.create")), facility_id: UUID = Depends(get_facility_context)):
    enrolled = db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id == payload.patient_id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE"))
    if enrolled is None:
        raise HTTPException(status_code=404, detail="PATIENT_NOT_IN_FACILITY")
    try:
        return check_coverage_eligibility(db, patient_id=payload.patient_id, coverage_id=payload.coverage_id, service_code=payload.service_code.strip().upper() if payload.service_code else None, service_type=payload.service_type.strip().upper() if payload.service_type else None, as_of=payload.as_of, actor_user_id=user.id, facility_id=facility_id)
    except EligibilityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("", response_model=PreAuthorizationResponse, status_code=status.HTTP_201_CREATED)
def create_preauthorization(payload: PreAuthorizationCreate, db: Session = Depends(get_db), user: Any = Depends(require_permission("encounters.create")), facility_id: UUID = Depends(get_facility_context), idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    if idempotency_key is not None:
        idempotency_key = idempotency_key.strip()
        if not idempotency_key or len(idempotency_key) > 150:
            raise HTTPException(status_code=400, detail="INVALID_IDEMPOTENCY_KEY")
    try:
        return request_preauthorization(db, facility_id=facility_id, actor_user_id=user.id, payload=payload, idempotency_key=idempotency_key)
    except PreAuthorizationError as exc:
        raise _error(exc) from exc


@router.post("/{authorization_id}/submit", response_model=PreAuthorizationSubmissionResponse)
def submit(authorization_id: UUID, payload: PreAuthorizationSubmission, db: Session = Depends(get_db), user: Any = Depends(require_permission("encounters.create")), facility_id: UUID = Depends(get_facility_context)):
    try:
        return submit_preauthorization(db, authorization_id=authorization_id, facility_id=facility_id, integration_id=payload.integration_id, actor_user_id=user.id)
    except (PreAuthorizationIntegrationError, PreAuthorizationError) as exc:
        raise _error(exc) from exc


@router.post("/{authorization_id}/decision", response_model=PreAuthorizationResponse)
def decide(authorization_id: UUID, payload: PreAuthorizationDecision, db: Session = Depends(get_db), user: Any = Depends(require_permission("encounters.create")), facility_id: UUID = Depends(get_facility_context)):
    try:
        return decide_preauthorization(db, authorization_id=authorization_id, facility_id=facility_id, actor_user_id=user.id, decision=payload)
    except PreAuthorizationError as exc:
        raise _error(exc) from exc
