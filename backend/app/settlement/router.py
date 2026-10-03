from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.claims.permissions import CLAIMS_RECONCILE
from app.database import get_db
from app.rbac.models import User
from app.settlement.models import ProviderPayment, SettlementBatch, SettlementObligation
from app.settlement.schemas import BatchCreateRequest, ObligationRequest, PaymentRequest, ReconcileRequest
from app.settlement.service import SettlementError, create_batch, generate_obligation, record_payment, reconcile_batch

router = APIRouter(prefix="/api/v1/settlements", tags=["Settlement"])


def err(exc: SettlementError):
    codes = {"CLAIM_NOT_FOUND": 404, "BATCH_NOT_FOUND": 404, "FACILITY_ACCESS_DENIED": 403}
    return HTTPException(status_code=codes.get(str(exc), 409), detail=str(exc))


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_RECONCILE)),
):
    _ = user
    ready = (
        db.scalar(
            select(func.count())
            .select_from(SettlementObligation)
            .where(
                SettlementObligation.facility_id == facility_id,
                SettlementObligation.status == "READY",
            )
        )
        or 0
    )
    in_batch = (
        db.scalar(
            select(func.count())
            .select_from(SettlementObligation)
            .where(
                SettlementObligation.facility_id == facility_id,
                SettlementObligation.status == "IN_BATCH",
            )
        )
        or 0
    )
    settled = (
        db.scalar(
            select(func.coalesce(func.sum(ProviderPayment.amount), 0)).where(
                ProviderPayment.facility_id == facility_id,
                ProviderPayment.status == "RECORDED",
            )
        )
        or 0
    )
    return {
        "ready_obligations": ready,
        "in_batch_obligations": in_batch,
        "provider_payments_recorded": float(settled),
    }


@router.get("/obligations")
def list_obligations(
    claim_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_RECONCILE)),
):
    """List obligations for facility; optional filter by claim_id / status. Phase 115."""
    _ = user
    q = select(SettlementObligation).where(SettlementObligation.facility_id == facility_id)
    if claim_id is not None:
        q = q.where(SettlementObligation.claim_id == claim_id)
    if status:
        q = q.where(SettlementObligation.status == status)
    rows = list(db.scalars(q.order_by(SettlementObligation.created_at.desc()).limit(limit)).all())
    return [
        {
            "id": str(r.id),
            "obligation_number": r.obligation_number,
            "claim_id": str(r.claim_id),
            "payer_id": str(r.payer_id),
            "submitted_amount": float(r.submitted_amount),
            "payable_amount": float(r.payable_amount),
            "patient_amount": float(r.patient_amount),
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/obligations")
def obligation(
    payload: ObligationRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_RECONCILE)),
):
    try:
        return generate_obligation(
            db, claim_id=payload.claim_id, facility_id=facility_id, actor_user_id=user.id
        )
    except SettlementError as e:
        raise err(e)


@router.post("/batches")
def batch(
    payload: BatchCreateRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_RECONCILE)),
):
    try:
        return create_batch(
            db, facility_id=facility_id, payer_id=payload.payer_id, actor_user_id=user.id
        )
    except SettlementError as e:
        raise err(e)


@router.post("/batches/{batch_id}/payments")
def payment(
    batch_id: UUID,
    payload: PaymentRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_RECONCILE)),
):
    try:
        return record_payment(
            db, batch_id=batch_id, facility_id=facility_id, payload=payload, actor_user_id=user.id
        )
    except SettlementError as e:
        raise err(e)


@router.post("/batches/{batch_id}/reconcile")
def reconcile(
    batch_id: UUID,
    payload: ReconcileRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_RECONCILE)),
):
    try:
        return reconcile_batch(
            db,
            batch_id=batch_id,
            facility_id=facility_id,
            received_amount=payload.received_amount,
            actor_user_id=user.id,
        )
    except SettlementError as e:
        raise err(e)


@router.get("/batches")
def batches(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_RECONCILE)),
):
    _ = user
    return list(
        db.scalars(
            select(SettlementBatch)
            .where(SettlementBatch.facility_id == facility_id)
            .order_by(SettlementBatch.created_at.desc())
            .limit(100)
        ).all()
    )
