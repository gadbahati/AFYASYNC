"""Citizen wallet routes — patient identity required."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_patient_identity
from app.citizen_wallet.service import benefits_transparency, charge_ledger, wallet_overview
from app.database import get_db
from app.portal.service import PortalError, audit_portal_view, require_patient_person_id
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/citizen-wallet", tags=["Citizen Wallet"])


def _person_id(user: User) -> UUID:
    try:
        return require_patient_person_id(user.person_id)
    except PortalError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err


@router.get("/overview")
def overview(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    person_id = _person_id(user)
    try:
        result = wallet_overview(db, person_id=person_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    audit_portal_view(
        db,
        user_id=user.id,
        person_id=person_id,
        action="CITIZEN_WALLET_OVERVIEW",
        resource_type="PERSON",
        resource_id=str(person_id),
    )
    return result


@router.get("/benefits")
def benefits(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    person_id = _person_id(user)
    try:
        result = benefits_transparency(db, person_id=person_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    audit_portal_view(
        db,
        user_id=user.id,
        person_id=person_id,
        action="CITIZEN_WALLET_BENEFITS",
        resource_type="PERSON",
        resource_id=str(person_id),
    )
    return result


@router.get("/charges")
def charges(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=100),
):
    person_id = _person_id(user)
    result = charge_ledger(db, person_id=person_id, limit=limit)
    audit_portal_view(
        db,
        user_id=user.id,
        person_id=person_id,
        action="CITIZEN_WALLET_CHARGES",
        resource_type="PERSON",
        resource_id=str(person_id),
    )
    return result
