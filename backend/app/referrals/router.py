from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_token_payload, require_permission
from app.database import get_db
from app.rbac.models import Staff, User
from app.referrals.schemas import ReferralCreate, ReferralOut, ReferralStatusUpdate, TransferCreate, TransferOut, TransferStatusUpdate
from app.referrals.service import ReferralError, create_referral, create_transfer, update_referral_status, update_transfer_status

router = APIRouter(prefix="/api/v1/referrals", tags=["Referrals"])


def _facility(token: dict) -> UUID:
    raw = token.get("facility_id")
    if not raw:
        raise HTTPException(status_code=403, detail="FACILITY_CONTEXT_REQUIRED")
    try:
        return UUID(raw)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=403, detail="INVALID_FACILITY_CONTEXT") from exc


def _resolve_staff(db: Session, user: User, facility_id: UUID) -> UUID:
    if user.person_id is None:
        raise HTTPException(status_code=403, detail="STAFF_CONTEXT_REQUIRED")
    staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == facility_id, Staff.status == "ACTIVE").limit(1))
    if staff is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return staff.id


@router.post("", response_model=ReferralOut, status_code=status.HTTP_201_CREATED)
def create(payload: ReferralCreate, user: User = Depends(require_permission("referrals.create")), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> ReferralOut:
    facility_id = _facility(token)
    try:
        return create_referral(db, facility_id, _resolve_staff(db, user, facility_id), payload.model_dump(), actor_user_id=user.id)
    except ReferralError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{referral_id}/status", response_model=ReferralOut)
def status_update(referral_id: UUID, payload: ReferralStatusUpdate, user: User = Depends(require_permission("referrals.manage")), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> ReferralOut:
    facility_id = _facility(token)
    try:
        return update_referral_status(db, facility_id, referral_id, payload.status, actor_user_id=user.id)
    except ReferralError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/transfers", response_model=TransferOut, status_code=status.HTTP_201_CREATED)
def create_transfer_endpoint(payload: TransferCreate, user: User = Depends(require_permission("referrals.transfer")), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> TransferOut:
    facility_id = _facility(token)
    try:
        return create_transfer(db, facility_id, _resolve_staff(db, user, facility_id), payload.model_dump(), actor_user_id=user.id)
    except ReferralError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/transfers/{transfer_id}/status", response_model=TransferOut)
def transfer_status(transfer_id: UUID, payload: TransferStatusUpdate, user: User = Depends(require_permission("referrals.manage")), token: dict = Depends(get_token_payload), db: Session = Depends(get_db)) -> TransferOut:
    facility_id = _facility(token)
    try:
        return update_transfer_status(db, facility_id, transfer_id, payload.status, actor_user_id=user.id)
    except ReferralError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
