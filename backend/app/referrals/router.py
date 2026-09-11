from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import Staff, User
from app.referrals.schemas import (
    ReferralCreate,
    ReferralListResponse,
    ReferralOut,
    ReferralStatusUpdate,
    TransferCreate,
    TransferListResponse,
    TransferOut,
    TransferStatusUpdate,
)
from app.referrals.service import (
    ReferralError,
    create_referral,
    create_transfer,
    get_referral_for_facility,
    get_transfer_for_facility,
    list_referrals_for_facility,
    list_transfers_for_facility,
    update_referral_status,
    update_transfer_status,
)

router = APIRouter(prefix="/api/v1/referrals", tags=["Referrals"])


def _resolve_staff(db: Session, user: User, facility_id: UUID) -> UUID:
    if user.person_id is None:
        raise HTTPException(status_code=403, detail="STAFF_CONTEXT_REQUIRED")
    staff = db.scalar(
        select(Staff).where(
            Staff.person_id == user.person_id,
            Staff.facility_id == facility_id,
            Staff.status == "ACTIVE",
        ).limit(1)
    )
    if staff is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return staff.id


def _error(exc: ReferralError) -> HTTPException:
    code = str(exc)
    mapping = {
        "ENCOUNTER_NOT_FOUND": 404,
        "REFERRAL_NOT_FOUND": 404,
        "TRANSFER_NOT_FOUND": 404,
        "DESTINATION_FACILITY_NOT_FOUND": 404,
        "DESTINATION_DEPARTMENT_NOT_FOUND": 404,
        "STAFF_NOT_FOUND": 404,
        "FACILITY_ACCESS_DENIED": 403,
        "ENCOUNTER_NOT_OPEN": 409,
        "DESTINATION_MUST_DIFFER": 400,
        "INVALID_REFERRAL": 400,
        "REFERRAL_NOT_READY_FOR_TRANSFER": 409,
        "INVALID_REFERRAL_TRANSITION": 409,
        "INVALID_TRANSFER_TRANSITION": 409,
    }
    return HTTPException(status_code=mapping.get(code, 400), detail=code)


@router.post("", response_model=ReferralOut, status_code=status.HTTP_201_CREATED)
def create(
    payload: ReferralCreate,
    user: User = Depends(require_permission("referrals.create")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> ReferralOut:
    try:
        return create_referral(
            db,
            facility_id,
            _resolve_staff(db, user, facility_id),
            payload.model_dump(),
            actor_user_id=user.id,
        )
    except ReferralError as exc:
        raise _error(exc) from exc


@router.get("", response_model=ReferralListResponse)
def list_referrals(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    role: Literal["all", "source", "destination"] = Query(default="all"),
    user: User = Depends(require_permission("referrals.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> ReferralListResponse:
    items, total = list_referrals_for_facility(db, facility_id, limit=limit, offset=offset, role=role)
    return ReferralListResponse(items=items, total=total, limit=limit, offset=offset)


# Transfer routes MUST be registered before /{referral_id} to avoid path capture
@router.post("/transfers", response_model=TransferOut, status_code=status.HTTP_201_CREATED)
def create_transfer_endpoint(
    payload: TransferCreate,
    user: User = Depends(require_permission("referrals.transfer")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> TransferOut:
    try:
        return create_transfer(
            db,
            facility_id,
            _resolve_staff(db, user, facility_id),
            payload.model_dump(),
            actor_user_id=user.id,
        )
    except ReferralError as exc:
        raise _error(exc) from exc


@router.get("/transfers", response_model=TransferListResponse)
def list_transfers(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    role: Literal["all", "source", "destination"] = Query(default="all"),
    user: User = Depends(require_permission("referrals.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> TransferListResponse:
    items, total = list_transfers_for_facility(db, facility_id, limit=limit, offset=offset, role=role)
    return TransferListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/transfers/{transfer_id}", response_model=TransferOut)
def get_transfer(
    transfer_id: UUID,
    user: User = Depends(require_permission("referrals.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> TransferOut:
    try:
        return get_transfer_for_facility(db, transfer_id, facility_id)
    except ReferralError as exc:
        raise _error(exc) from exp


@router.post("/transfers/{transfer_id}/status", response_model=TransferOut)
def transfer_status(
    transfer_id: UUID,
    payload: TransferStatusUpdate,
    user: User = Depends(require_permission("referrals.manage")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> TransferOut:
    try:
        return update_transfer_status(db, facility_id, transfer_id, payload.status, actor_user_id=user.id)
    except ReferralError as exc:
        raise _error(exc) from exp


@router.get("/{referral_id}", response_model=ReferralOut)
def get_referral(
    referral_id: UUID,
    user: User = Depends(require_permission("referrals.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> ReferralOut:
    try:
        return get_referral_for_facility(db, referral_id, facility_id)
    except ReferralError as exc:
        raise _error(exc) from exp


@router.post("/{referral_id}/status", response_model=ReferralOut)
def status_update(
    referral_id: UUID,
    payload: ReferralStatusUpdate,
    user: User = Depends(require_permission("referrals.manage")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> ReferralOut:
    try:
        return update_referral_status(db, facility_id, referral_id, payload.status, actor_user_id=user.id)
    except ReferralError as exc:
        raise _error(exc) from exp
