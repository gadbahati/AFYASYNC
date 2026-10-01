from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.settlement.recovery import RevenueRecoveryCase,open_recovery,update_recovery,recovery_overview
from pydantic import BaseModel,Field
router=APIRouter(prefix="/api/v1/revenue-recovery",tags=["Revenue Recovery"])
class OpenRecovery(BaseModel):
    reconciliation_id:UUID
    reason:str=Field(min_length=2,max_length=60)
    priority:str="NORMAL"
    notes:str|None=None
class UpdateRecovery(BaseModel):
    status:str
    recovered_amount:Decimal=Field(ge=0)
    note:str|None=None
def e(x): return HTTPException(status_code=403 if str(x)=="FACILITY_ACCESS_DENIED" else 409,detail=str(x))
@router.get("/overview")
def overview(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    _=user;return recovery_overview(db,facility_id)
@router.get("/cases")
def cases(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    _=user;return list(db.scalars(select(RevenueRecoveryCase).where(RevenueRecoveryCase.facility_id==facility_id).order_by(RevenueRecoveryCase.updated_at.desc()).limit(200)).all())
@router.post("/cases")
def create(payload:OpenRecovery,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return open_recovery(db,payload.reconciliation_id,facility_id,payload.reason,payload.priority,payload.notes,user.id)
    except ValueError as x:raise e(x)
@router.patch("/cases/{case_id}")
def update(case_id:UUID,payload:UpdateRecovery,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return update_recovery(db,case_id,facility_id,payload.status,payload.recovered_amount,payload.note,user.id)
    except ValueError as x:raise e(x)
