from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.admissions.schemas import AdmissionCreate, AdmissionResponse, SHAMemberLookupResponse
from app.admissions.service import lookup_sha_member, start_admission
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/admissions", tags=["Admissions"])


def _error(exc: ValueError) -> HTTPException:
    code = str(exc)
    mapping = {
        "SHA_MEMBER_NOT_FOUND": 404,
        "SHA_COVERAGE_NOT_ACTIVE": 409,
        "SHA_COVERAGE_EXPIRED": 409,
        "VERIFIED_SHA_COVERAGE_REQUIRED": 409,
        "PATIENT_NOT_FOUND": 404,
        "PATIENT_NOT_IN_FACILITY": 404,
        "BENEFIT_PACKAGE_NOT_FOUND": 404,
        "INPATIENT_SHA_PACKAGE_REQUIRED": 400,
        "PATIENT_ALREADY_ADMITTED": 409,
    }
    return HTTPException(status_code=mapping.get(code, 400), detail=code)


@router.get("/sha-member", response_model=SHAMemberLookupResponse)
def verify_sha_member(
    membership_number: str = Query(min_length=3, max_length=100),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("encounters.read")),
):
    _ = user
    try:
        return lookup_sha_member(db, membership_number=membership_number.strip(), facility_id=facility_id)
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("", response_model=AdmissionResponse, status_code=status.HTTP_201_CREATED)
def admit(
    payload: AdmissionCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("encounters.create")),
):
    try:
        return start_admission(db, patient_id=payload.patient_id, facility_id=facility_id, department_id=payload.department_id, benefit_package_code=payload.benefit_package_code, ward=payload.ward, bed=payload.bed, diagnosis=payload.diagnosis, created_by=user.id, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(exc) from exc
