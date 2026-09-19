"""API routes for SHA Treat Abroad — hardened."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_facility_context
from app.database import get_db
from app.rbac.models import Staff, User
from app.treat_abroad.schemas import (
    ApprovedProcedureOut,
    OverseasCaseCreate,
    OverseasCaseOut,
    OverseasCaseUpdate,
)
from app.treat_abroad.seed import seed_approved_procedures
from app.treat_abroad.service import (
    create_case,
    get_case,
    list_approved_procedures,
    list_cases,
    update_case,
)

router = APIRouter(prefix="/api/v1/treat-abroad", tags=["Treat Abroad"])


def _staff_for_user(db: Session, user: User, facility_id: UUID) -> UUID:
    if user.person_id is None:
        raise HTTPException(status_code=403, detail="STAFF_PROFILE_REQUIRED")
    staff = db.scalar(
        select(Staff).where(
            Staff.person_id == user.person_id,
            Staff.facility_id == facility_id,
            Staff.status == "ACTIVE",
        )
    )
    if staff is None:
        raise HTTPException(status_code=403, detail="STAFF_NOT_AT_FACILITY")
    return staff.id


def _map_create_error(code: str) -> int:
    if code in {"PATIENT_NOT_FOUND", "PROCEDURE_NOT_FOUND_OR_INACTIVE"}:
        return status.HTTP_404_NOT_FOUND
    if code == "TOO_MANY_OPEN_CASES":
        return status.HTTP_409_CONFLICT
    return status.HTTP_400_BAD_REQUEST


@router.get("/procedures", response_model=list[ApprovedProcedureOut])
def get_approved_procedures(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    """List active SHA-approved overseas procedures (facility staff only)."""
    _ = facility_id  # ensure facility-scoped session
    rows = list_approved_procedures(db, active_only=True)
    if not rows:
        seed_approved_procedures(db)
        db.commit()
        rows = list_approved_procedures(db, active_only=True)
    return rows


@router.post("/cases", response_model=OverseasCaseOut, status_code=status.HTTP_201_CREATED)
def create_overseas_case(
    payload: OverseasCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    if payload.facility_id != facility_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FACILITY_MISMATCH",
        )
    clinician_id = _staff_for_user(db, current_user, facility_id)
    data = payload.model_copy(update={"referring_clinician_id": clinician_id})
    try:
        case = create_case(db, payload=data, created_by=current_user.id)
        db.commit()
        db.refresh(case)
        return case
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=_map_create_error(code), detail=code) from exc


@router.get("/cases", response_model=list[OverseasCaseOut])
def list_overseas_cases(
    patient_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    return list_cases(
        db,
        facility_id=facility_id,
        patient_id=patient_id,
        status=status_filter,
    )


@router.get("/cases/{case_id}", response_model=OverseasCaseOut)
def get_overseas_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    try:
        return get_case(db, case_id, facility_id=facility_id)
    except ValueError as exc:
        code = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND
            if code == "CASE_NOT_FOUND"
            else status.HTTP_403_FORBIDDEN
        )
        raise HTTPException(status_code=status_code, detail=code) from exc


@router.patch("/cases/{case_id}", response_model=OverseasCaseOut)
def patch_overseas_case(
    case_id: UUID,
    payload: OverseasCaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    try:
        case = get_case(db, case_id, facility_id=facility_id)
        updated = update_case(
            db, case=case, payload=payload, actor_user_id=current_user.id
        )
        db.commit()
        db.refresh(updated)
        return updated
    except ValueError as exc:
        detail = str(exc)
        if detail.startswith("INVALID_STATUS_TRANSITION") or detail == "CASE_CLOSED":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
        if detail == "CASE_NOT_FOUND":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        if detail == "FACILITY_ACCESS_DENIED":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail) from exc
        if detail in {"AMOUNT_EXCEEDS_PROCEDURE_CAP", "INVALID_AMOUNT"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
