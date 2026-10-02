from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.sla_service import upsert_policy,list_policies,denial_intelligence,sync_sla,sla_overview,payer_sla_performance,escalation_queue,sla_events
router=APIRouter(prefix="/api/v1/payer-sla",tags=["Payer SLA & Denial Intelligence"])
class SLAPolicyIn(BaseModel):
    payer_id:UUID
    denial_response_hours:int=Field(48,ge=1,le=8760)
    resolution_hours:int=Field(168,ge=1,le=8760)
    appeal_hours:int=Field(120,ge=1,le=8760)
    escalation_hours:int=Field(24,ge=1,le=8760)
    notes:str|None=None
def err(e):return HTTPException(status_code=404 if str(e)=="PAYER_NOT_FOUND" else 403 if str(e)=="FACILITY_ACCESS_DENIED" else 409,detail=str(e))
@router.get("/policies")
def policies(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return list_policies(db,facility_id)
@router.put("/policies")
def save(payload:SLAPolicyIn,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return {"id":str(upsert_policy(db,facility_id,**payload.model_dump(),actor_id=user.id).id)}
    except ValueError as e:raise err(e)
@router.get("/denials")
def denials(days:int=Query(90,ge=1,le=730),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return denial_intelligence(db,facility_id,days)
@router.get("/overview")
def overview(days:int=Query(90,ge=1,le=730),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return {"sla":sla_overview(db,facility_id),"performance":payer_sla_performance(db,facility_id,days),"denials":denial_intelligence(db,facility_id,days)}
@router.get("/escalation-queue")
def escalation(days:int=Query(90,ge=1,le=730),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return escalation_queue(db,facility_id)
@router.get("/{case_id}/events")
def events(case_id:UUID,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return [{"id":str(x.id),"event_type":x.event_type,"from_level":x.from_level,"to_level":x.to_level,"note":x.note,"actor_id":str(x.actor_id) if x.actor_id else None,"created_at":x.created_at.isoformat() if x.created_at else None} for x in sla_events(db,facility_id,case_id)]
    except ValueError as e:raise err(e)
@router.post("/sync")
def sync(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return sync_sla(db,facility_id,user.id)
