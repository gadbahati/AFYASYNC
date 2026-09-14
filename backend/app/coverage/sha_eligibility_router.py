from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.coverage.sha_eligibility_schemas import SHAEligibilityRequest, SHAEligibilityResponse
from app.coverage.sha_eligibility_service import SHAEligibilityError, verify_sha_eligibility
from app.database import get_db
from app.rbac.models import User

SHA_ELIGIBILITY_VERIFY = "coverage.sha.verify"

router = APIRouter(prefix="/api/v1/coverage/sha", tags=["SHA Eligibility"])

_ERROR_STATUS = {
    "PATIENT_NOT_IN_FACILITY": 404,
    "AFYA_ID_NOT_ACTIVE": 404,
    "SHA_PAYER_NOT_CONFIGURED": 503,
    "SHA_INTEGRATION_NOT_CONFIGURED": 503,
    "SHA_CONNECTOR_NOT_CONFIGURED": 503,
    "SHA_ELIGIBILITY_UNAVAILABLE": 503,
    "SHA_ELIGIBILITY_FAILED": 502,
    "SHA_PLAN_NOT_CONFIGURED": 409,
    "SHA_MEMBERSHIP_MISMATCH": 422,
    "INVALID_SHA_RESPONSE": 502,
    "INVALID_SHA_RESPONSE_MEMBERSHIP": 502,
    "INVALID_SHA_RESPONSE_PLAN": 502,
    "INVALID_SHA_RESPONSE_DATES": 502,
    "INVALID_SHA_RESPONSE_START_DATE": 502,
    "INVALID_SHA_RESPONSE_END_DATE": 502,
}


@router.post("/eligibility", response_model=SHAEligibilityResponse)
def check_sha_eligibility(
    payload: SHAEligibilityRequest,
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(SHA_ELIGIBILITY_VERIFY)),
    db: Session = Depends(get_db),
) -> SHAEligibilityResponse:
    try:
        return verify_sha_eligibility(
            db,
            facility_id=facility_id,
            person_id=payload.person_id,
            membership_number=payload.membership_number,
            actor_user_id=user.id,
        )
    except SHAEligibilityError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=_ERROR_STATUS.get(code, status.HTTP_400_BAD_REQUEST),
            detail={"code": code, "message": code.replace("_", " ").title()},
        ) from exc
