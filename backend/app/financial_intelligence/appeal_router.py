from datetime import datetime
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.appeal_service import create_appeal,update_appeal,list_appeals,overview,events
router=APIRouter(prefix="/api/v1/denial-appeals",tags=["Denial Appeals"])
class AppealCreate(BaseModel):
    clearinghouse_case_id:UUID
    due_at:datetime|None=None
    grounds:str|None=None
class AppealUpdate(BaseModel):
    status:str|None=None
    assigned_to:UUID|None=None
    due_at:datetime|None=None
    grounds:str|None=None
    evidence_checklist:dict|None=None
    submission_notes:str|None=None
    external_reference:str|None=None
    outcome:str|None=None
    outcome_notes:str|None=None
def err(e):return HTTPException(status_code=403 if str(e)=="FACILITY_ACCESS_DENIED" else 409,detail=str(e))
def out(a):return {"id":str(a.id),"appeal_number":a.appeal_number,"clearinghouse_case_id":str(a.clearinghouse_case_id),"resolution_case_id":str(a.resolution_case_id) if a.resolution_case_id else None,"status":a.status,"assigned_to":str(a.assigned_to) if a.assigned_to else None,"due_at":a.due_at.isoformat() if a.due_at else None,"submitted_at":a.submitted_at.isoformat() if a.submitted_at else None,"resolved_at":a.resolved_at.isoformat() if a.resolved_at else None,"external_reference":a.external_reference,"grounds":a.grounds,"evidence_checklist":a.evidence_checklist,"submission_notes":a.submission_notes,"outcome":a.outcome,"outcome_notes":a.outcome_notes}
@router.get("/overview")
def appeal_overview(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return overview(db,facility_id)
@router.get("")
def appeals(status:str|None=Query(None),limit:int=Query(200,ge=1,le=500),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return [out(a) for a in list_appeals(db,facility_id,status,limit)]
@router.post("")
def create(payload:AppealCreate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return out(create_appeal(db,facility_id,payload.clearinghouse_case_id,user.id,payload.due_at,payload.grounds))
    except ValueError as e:raise err(e)
@router.patch("/{appeal_id}")
def update(appeal_id:UUID,payload:AppealUpdate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return out(update_appeal(db,facility_id,appeal_id,actor_id=user.id,**payload.model_dump()))
    except ValueError as e:raise err(e)
@router.get("/{appeal_id}/events")
def appeal_events(appeal_id:UUID,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return [{"id":str(x.id),"event_type":x.event_type,"from_status":x.from_status,"to_status":x.to_status,"actor_id":str(x.actor_id) if x.actor_id else None,"note":x.note,"created_at":x.created_at.isoformat() if x.created_at else None} for x in events(db,facility_id,appeal_id)]
    except ValueError as e:raise err(e)
