from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context, require_permission
from app.claims.permissions import CLAIMS_RECONCILE
from app.database import get_db
from app.rbac.models import User
from app.settlement.models import SettlementObligation, SettlementBatch, ProviderPayment
from app.settlement.schemas import ObligationRequest, BatchCreateRequest, PaymentRequest, ReconcileRequest
from app.settlement.service import SettlementError, generate_obligation, create_batch, record_payment, reconcile_batch

router=APIRouter(prefix="/api/v1/settlements",tags=["Settlement"])

def err(exc: SettlementError):
    codes={"CLAIM_NOT_FOUND":404,"BATCH_NOT_FOUND":404,"FACILITY_ACCESS_DENIED":403}
    return HTTPException(status_code=codes.get(str(exc),409),detail=str(exc))

@router.get("/overview")
def overview(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission(CLAIMS_RECONCILE))):
    _=user
    ready=db.scalar(select(func.count()).select_from(SettlementObligation).where(SettlementObligation.facility_id==facility_id,SettlementObligation.status=="READY")) or 0
    in_batch=db.scalar(select(func.count()).select_from(SettlementObligation).where(SettlementObligation.facility_id==facility_id,SettlementObligation.status=="IN_BATCH")) or 0
    settled=db.scalar(select(func.coalesce(func.sum(ProviderPayment.amount),0)).where(ProviderPayment.facility_id==facility_id,ProviderPayment.status=="RECORDED")) or 0
    return {"ready_obligations":ready,"in_batch_obligations":in_batch,"provider_payments_recorded":float(settled)}

@router.post("/obligations")
def obligation(payload:ObligationRequest,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission(CLAIMS_RECONCILE))):
    try:return generate_obligation(db,claim_id=payload.claim_id,facility_id=facility_id,actor_user_id=user.id)
    except SettlementError as e:raise err(e)

@router.post("/batches")
def batch(payload:BatchCreateRequest,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission(CLAIMS_RECONCILE))):
    try:return create_batch(db,facility_id=facility_id,payer_id=payload.payer_id,actor_user_id=user.id)
    except SettlementError as e:raise err(e)

@router.post("/batches/{batch_id}/payments")
def payment(batch_id:UUID,payload:PaymentRequest,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission(CLAIMS_RECONCILE))):
    try:return record_payment(db,batch_id=batch_id,facility_id=facility_id,payload=payload,actor_user_id=user.id)
    except SettlementError as e:raise err(e)

@router.post("/batches/{batch_id}/reconcile")
def reconcile(batch_id:UUID,payload:ReconcileRequest,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission(CLAIMS_RECONCILE))):
    try:return reconcile_batch(db,batch_id=batch_id,facility_id=facility_id,received_amount=payload.received_amount,actor_user_id=user.id)
    except SettlementError as e:raise err(e)

@router.get("/batches")
def batches(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission(CLAIMS_RECONCILE))):
    _=user
    return list(db.scalars(select(SettlementBatch).where(SettlementBatch.facility_id==facility_id).order_by(SettlementBatch.created_at.desc()).limit(100)).all())
