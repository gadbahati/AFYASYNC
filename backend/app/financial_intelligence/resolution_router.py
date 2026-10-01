from datetime import datetime
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.resolution import sync_resolution_queue,list_resolution,overview,update_resolution,events
router=APIRouter(prefix="/api/v1/revenue-resolution",tags=["Revenue Resolution"])
class ResolutionUpdate(BaseModel):
    status:str="IN_REVIEW"
    assigned_to:UUID|None=None
    due_at:datetime|None=None
    root_cause:str|None=None
    resolution_action:str|None=None
    notes:str|None=None

def err(e):return HTTPException(status_code=403 if str(e)=="FACILITY_ACCESS_DENIED" else 409,detail=str(e))
@router.get("/overview")
def resolution_overview(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    _=user;return overview(db,facility_id)
@router.get("")
def resolution_cases(status:str|None=Query(None),limit:int=Query(200,ge=1,le=500),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    _=user
    return [{"id":str(x.id),"case_number":x.case_number,"source_type":x.source_type,"source_id":str(x.source_id),"claim_id":str(x.claim_id) if x.claim_id else None,"payer_id":str(x.payer_id) if x.payer_id else None,"title":x.title,"priority":x.priority,"status":x.status,"assigned_to":str(x.assigned_to) if x.assigned_to else None,"due_at":x.due_at.isoformat() if x.due_at else None,"amount_at_risk":float(x.amount_at_risk or 0),"root_cause":x.root_cause,"resolution_action":x.resolution_action,"notes":x.notes} for x in list_resolution(db,facility_id,status,limit)]
@router.post("/sync")
def sync(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return sync_resolution_queue(db,facility_id,user.id)
@router.patch("/{case_id}")
def update(case_id:UUID,payload:ResolutionUpdate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:
        x=update_resolution(db,facility_id,case_id,payload.status,payload.assigned_to,payload.due_at,payload.root_cause,payload.resolution_action,payload.notes,user.id)
        return {"id":str(x.id),"status":x.status,"assigned_to":str(x.assigned_to) if x.assigned_to else None,"due_at":x.due_at.isoformat() if x.due_at else None}
    except ValueError as e:raise err(e)
@router.get("/{case_id}/events")
def case_events(case_id:UUID,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    _=user
    try:return [{"id":str(x.id),"event_type":x.event_type,"from_status":x.from_status,"to_status":x.to_status,"actor_id":str(x.actor_id) if x.actor_id else None,"note":x.note,"created_at":x.created_at.isoformat() if x.created_at else None} for x in events(db,facility_id,case_id)]
    except ValueError as e:raise err(e)
