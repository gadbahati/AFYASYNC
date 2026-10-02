from uuid import UUID
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.sla_service import upsert_policy,list_policies,denial_intelligence,sync_sla,sla_overview,payer_sla_performance,escalation_queue,sla_events
from app.financial_intelligence.appeal_service import create_appeal,update_appeal,list_appeals,overview as appeal_overview,events as appeal_events
router=APIRouter(prefix="/api/v1/payer-sla",tags=["Payer SLA & Denial Intelligence"])
class SLAPolicyIn(BaseModel):
    payer_id:UUID
    denial_response_hours:int=Field(48,ge=1,le=8760)
    resolution_hours:int=Field(168,ge=1,le=8760)
    appeal_hours:int=Field(120,ge=1,le=8760)
    escalation_hours:int=Field(24,ge=1,le=8760)
    notes:str|None=None
class AppealCreate(BaseModel):
    clearinghouse_case_id:UUID
    due_at:datetime|None=None
    grounds:str|None=None
class AppealUpdate(BaseModel):
    status:str|None=None
    assigned_to:UUID|None=None
    due_at:object|None=None
    grounds:str|None=None
    evidence_checklist:dict|None=None
    submission_notes:str|None=None
    external_reference:str|None=None
    outcome:str|None=None
    outcome_notes:str|None=None
def err(e):return HTTPException(status_code=404 if str(e) in {"PAYER_NOT_FOUND","APPEAL_NOT_FOUND"} else 403 if str(e)=="FACILITY_ACCESS_DENIED" else 409,detail=str(e))
def appeal_out(a):return {"id":str(a.id),"appeal_number":a.appeal_number,"clearinghouse_case_id":str(a.clearinghouse_case_id),"resolution_case_id":str(a.resolution_case_id) if a.resolution_case_id else None,"status":a.status,"assigned_to":str(a.assigned_to) if a.assigned_to else None,"due_at":a.due_at.isoformat() if a.due_at else None,"submitted_at":a.submitted_at.isoformat() if a.submitted_at else None,"resolved_at":a.resolved_at.isoformat() if a.resolved_at else None,"external_reference":a.external_reference,"grounds":a.grounds,"evidence_checklist":a.evidence_checklist,"submission_notes":a.submission_notes,"outcome":a.outcome,"outcome_notes":a.outcome_notes}
@router.get("/policies")
def policies(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return list_policies(db,facility_id)
@router.put("/policies")
def save(payload:SLAPolicyIn,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return {"id":str(upsert_policy(db,facility_id,**payload.model_dump(),actor_id=user.id).id)}
    except ValueError as e:raise err(e)
@router.get("/denials")
def denials(days:int=Query(90,ge=1,le=730),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return denial_intelligence(db,facility_id,days)
@router.get("/overview")
def overview(days:int=Query(90,ge=1,le=730),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return {"sla":sla_overview(db,facility_id),"performance":payer_sla_performance(db,facility_id,days),"denials":denial_intelligence(db,facility_id,days),"appeals":appeal_overview(db,facility_id)}
@router.get("/escalation-queue")
def escalation(days:int=Query(90,ge=1,le=730),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return escalation_queue(db,facility_id)
@router.get("/appeals")
def appeals(status:str|None=Query(None),limit:int=Query(200,ge=1,le=500),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return [appeal_out(a) for a in list_appeals(db,facility_id,status,limit)]
@router.post("/appeals")
def create(payload:AppealCreate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return appeal_out(create_appeal(db,facility_id,payload.clearinghouse_case_id,user.id,payload.due_at,payload.grounds))
    except ValueError as e:raise err(e)
@router.patch("/appeals/{appeal_id}")
def update(appeal_id:UUID,payload:AppealUpdate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return appeal_out(update_appeal(db,facility_id,appeal_id,actor_id=user.id,**payload.model_dump()))
    except ValueError as e:raise err(e)
@router.get("/appeals/{appeal_id}/events")
def appeal_history(appeal_id:UUID,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return [{"id":str(x.id),"event_type":x.event_type,"from_status":x.from_status,"to_status":x.to_status,"actor_id":str(x.actor_id) if x.actor_id else None,"note":x.note,"created_at":x.created_at.isoformat() if x.created_at else None} for x in appeal_events(db,facility_id,appeal_id)]
    except ValueError as e:raise err(e)
@router.get("/{case_id}/events")
def events(case_id:UUID,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return [{"id":str(x.id),"event_type":x.event_type,"from_level":x.from_level,"to_level":x.to_level,"note":x.note,"actor_id":str(x.actor_id) if x.actor_id else None,"created_at":x.created_at.isoformat() if x.created_at else None} for x in sla_events(db,facility_id,case_id)]
    except ValueError as e:raise err(e)
@router.post("/sync")
def sync(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return sync_sla(db,facility_id,user.id)
