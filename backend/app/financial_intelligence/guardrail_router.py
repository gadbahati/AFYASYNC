from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.guardrail_service import sync_guardrails,overview,list_guardrails,update_guardrail,events
from app.financial_intelligence.cash_resolution_service import close_loop, sync_guardrail_work, sync_settlement_recovery
from app.financial_intelligence.contract_cash_command import contract_cash_command

router=APIRouter(prefix="/api/v1/contract-guardrails",tags=["Contract Compliance Guardrails"])

class SyncBody(BaseModel):
    limit:int=200

class UpdateBody(BaseModel):
    status:str
    note:str|None=None

@router.get("/command")
def command(days:int=Query(90,ge=7,le=365),db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return contract_cash_command(db,facility_id,days)

@router.get("/overview")
def get_overview(db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return overview(db,facility_id)

@router.get("")
def get_items(status:str|None=Query(None),limit:int=Query(200,ge=1,le=500),db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return [serialize(x) for x in list_guardrails(db,facility_id,status,limit)]

@router.post("/sync")
def sync(payload:SyncBody,db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return sync_guardrails(db,facility_id,user.id,payload.limit)

@router.patch("/{guardrail_id}")
def update(guardrail_id:UUID,payload:UpdateBody,db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try: return serialize(update_guardrail(db,facility_id,guardrail_id,payload.status,user.id,payload.note))
    except ValueError as e: raise HTTPException(status_code=409,detail=str(e))

@router.get("/{guardrail_id}/events")
def get_events(guardrail_id:UUID,db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try: rows=events(db,facility_id,guardrail_id)
    except ValueError as e: raise HTTPException(status_code=404,detail=str(e))
    return [{"id":str(x.id),"event_type":x.event_type,"from_status":x.from_status,"to_status":x.to_status,"actor_id":str(x.actor_id) if x.actor_id else None,"note":x.note,"metadata":x.metadata_json,"created_at":x.created_at.isoformat() if x.created_at else None} for x in rows]

@router.post("/close-loop")
def run_close_loop(payload:SyncBody,db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return close_loop(db,facility_id,user.id,payload.limit)

@router.post("/work-queue")
def guardrails_to_work(payload:SyncBody,db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return sync_guardrail_work(db,facility_id,user.id,payload.limit)

@router.post("/recovery")
def settlement_recovery(payload:SyncBody,db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return sync_settlement_recovery(db,facility_id,user.id,payload.limit)

def serialize(x):
    return {"id":str(x.id),"contract_id":str(x.contract_id) if x.contract_id else None,"claim_id":str(x.claim_id) if x.claim_id else None,"payer_id":str(x.payer_id) if x.payer_id else None,"guardrail_type":x.guardrail_type,"severity":x.severity,"status":x.status,"title":x.title,"expected_amount":float(x.expected_amount or 0),"actual_amount":float(x.actual_amount or 0),"amount_at_risk":float(x.amount_at_risk or 0),"detail":x.detail,"evidence":x.evidence,"assigned_to":str(x.assigned_to) if x.assigned_to else None,"resolved_at":x.resolved_at.isoformat() if x.resolved_at else None,"created_at":x.created_at.isoformat() if x.created_at else None}
