from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_db, get_facility_context, require_permission
from app.auth.models import User
from app.preauthorizations.schemas import PreAuthorizationCreate, PreAuthorizationDecision, PreAuthorizationResponse
from app.preauthorizations.service import PreAuthorizationError, decide_preauthorization, request_preauthorization

router = APIRouter(prefix="/api/v1/preauthorizations", tags=["Preauthorizations"])


def _error(exc: PreAuthorizationError) -> HTTPException:
    code = str(exc)
    mapping = {
        "PATIENT_NOT_IN_FACILITY": status.HTTP_404_NOT_FOUND,
        "COVERAGE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "PREAUTH_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "FACILITY_ACCESS_DENIED": status.HTTP_403_FORBIDDEN,
        "VERIFIED_COVERAGE_REQUIRED": status.HTTP_409_CONFLICT,
        "COVERAGE_NOT_ACTIVE": status.HTTP_409_CONFLICT,
        "COVERAGE_EXPIRED": status.HTTP_409_CONFLICT,
        "SHA_PAYER_REQUIRED": status.HTTP_400_BAD_REQUEST,
        "BENEFIT_PACKAGE_NOT_FOUND": status.HTTP_400_BAD_REQUEST,
        "INPATIENT_SHA_PACKAGE_REQUIRED": status.HTTP_400_BAD_REQUEST,
        "PREAUTH_NOT_DECIDABLE": status.HTTP_409_CONFLICT,
        "APPROVED_AMOUNT_EXCEEDS_REQUEST": status.HTTP_400_BAD_REQUEST,
        "REJECTED_AMOUNT_MUST_BE_ZERO": status.HTTP_400_BAD_REQUEST,
    }
    return HTTPException(status_code=mapping.get(code, status.HTTP_400_BAD_REQUEST), detail=code)


@router.post("", response_model=PreAuthorizationResponse, status_code=status.HTTP_201_CREATED)
def create_preauthorization(
    payload: PreAuthorizationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("encounters.create")),
    facility_id: UUID = Depends(get_facility_context),
):
    try:
        return request_preauthorization(db, facility_id=facility_id, actor_user_id=user.id, payload=payload)
    except PreAuthorizationError as exc:
        raise _error(exc) from exc


@router.post("/{authorization_id}/decision", response_model=PreAuthorizationResponse)
def decide(
    authorization_id: UUID,
    payload: PreAuthorizationDecision,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("encounters.create")),
    facility_id: UUID = Depends(get_facility_context),
):
    try:
        return decide_preauthorization(db, authorization_id=authorization_id, facility_id=facility_id, actor_user_id=user.id, decision=payload)
    except PreAuthorizationError as exc:
        raise _error(exc) from exc
