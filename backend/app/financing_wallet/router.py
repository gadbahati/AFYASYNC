from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.claims.permissions import CLAIMS_RECONCILE
from app.database import get_db
from app.financing_wallet.schemas import ContributionRequest, ApplyRequest
from app.financing_wallet.service import FinancingWalletError, summary, contribute, apply_to_invoice, reconcile_patient_responsibility
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/financing-wallet", tags=["Financing Wallet"])


def _err(exc: FinancingWalletError) -> HTTPException:
    codes = {
        "PERSON_NOT_FOUND": 404, "INVOICE_ACCESS_DENIED": 404, "INVOICE_NOT_OPEN": 409,
        "INSUFFICIENT_WALLET_BALANCE": 409, "AMOUNT_EXCEEDS_PATIENT_BALANCE": 409,
    }
    return HTTPException(status_code=codes.get(str(exc), 409), detail=str(exc))


@router.get("/{person_id}")
def wallet(person_id: UUID, limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db),
           facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_RECONCILE))):
    try:
        return summary(db, person_id, limit)
    except FinancingWalletError as exc:
        raise _err(exc) from exc


@router.get("/{person_id}/transactions")
def transactions(person_id: UUID, limit: int = Query(100, ge=1, le=100), db: Session = Depends(get_db),
                 facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_RECONCILE))):
    try:
        return summary(db, person_id, limit)["transactions"]
    except FinancingWalletError as exc:
        raise _err(exc) from exc


@router.post("/{person_id}/contributions")
def add_contribution(person_id: UUID, payload: ContributionRequest, db: Session = Depends(get_db),
                     facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_RECONCILE))):
    try:
        return contribute(db, person_id=person_id, facility_id=facility_id, amount=payload.amount,
                          reference=payload.reference, source_type=payload.source_type,
                          description=payload.description, actor_user_id=user.id)
    except FinancingWalletError as exc:
        raise _err(exc) from exc


@router.post("/{person_id}/apply")
def apply(person_id: UUID, payload: ApplyRequest, db: Session = Depends(get_db),
          facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_RECONCILE))):
    try:
        return apply_to_invoice(db, person_id=person_id, facility_id=facility_id, invoice_id=payload.invoice_id,
                                amount=payload.amount, reference=payload.reference, description=payload.description,
                                actor_user_id=user.id)
    except FinancingWalletError as exc:
        raise _err(exc) from exc


@router.post("/{person_id}/reconcile")
def reconcile(person_id: UUID, db: Session = Depends(get_db),
              facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_RECONCILE))):
    try:
        return reconcile_patient_responsibility(db, person_id=person_id, facility_id=facility_id, actor_user_id=user.id)
    except FinancingWalletError as exc:
        raise _err(exc) from exc
