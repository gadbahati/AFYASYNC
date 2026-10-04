from datetime import datetime
from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.negotiation_service import create_case,list_cases,update_case,add_item,update_item,items,overview,events

router=APIRouter(prefix="/api/v1/payer-negotiation",tags=["Payer Negotiation Workspace"])
class CaseCreate(BaseModel):
    contract_id:UUID
    objective:str|None=None
    due_at:datetime|None=None
class CaseUpdate(BaseModel):
    status:str|None=None
    owner_id:UUID|None=None
    due_at:datetime|None=None
    objective:str|None=None
    opening_position:dict|None=None
    target_position:dict|None=None
    proposed_terms:dict|None=None
    accepted_terms:dict|None=None
    notes:str|None=None
class ItemCreate(BaseModel):
    item_type:str
    title:str
    current_value:dict|None=None
    requested_value:dict|None=None
    rationale:str|None=None
    priority:str="MEDIUM"
class ItemUpdate(BaseModel):
    status:str|None=None
    requested_value:dict|None=None
    rationale:str|None=None
    priority:str|None=None
    external_response:str|None=None
def err(e):
    return HTTPException(status_code=404 if str(e).endswith("NOT_FOUND") else 409,detail=str(e))
def item_out(x):
    return {"id":str(x.id),"case_id":str(x.case_id),"item_type":x.item_type,"title":x.title,"current_value":x.current_value,"requested_value":x.requested_value,"rationale":x.rationale,"priority":x.priority,"status":x.status,"external_response":x.external_response}
def event_out(x):
    return {"id":str(x.id),"event_type":x.event_type,"from_status":x.from_status,"to_status":x.to_status,"actor_id":str(x.actor_id) if x.actor_id else None,"note":x.note,"metadata":x.event_metadata,"created_at":x.created_at.isoformat() if x.created_at else None}
@router.get("/overview")
def get_overview(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return overview(db,facility_id)
@router.get("")
def get_cases(status:str|None=Query(None),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return [__import__("json").loads(__import__("json").dumps({**{"id":str(x.id),"case_number":x.case_number,"contract_id":str(x.contract_id),"status":x.status,"owner_id":str(x.owner_id) if x.owner_id else None,"due_at":x.due_at.isoformat() if x.due_at else None,"objective":x.objective,"opening_position":x.opening_position,"target_position":x.target_position,"evidence_snapshot":x.evidence_snapshot,"proposed_terms":x.proposed_terms,"accepted_terms":x.accepted_terms,"notes":x.notes}})) for x in list_cases(db,facility_id,status)]
@router.post("")
def post_case(payload:CaseCreate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return __import__("json").loads(__import__("json").dumps({**{"id":str((x:=create_case(db,facility_id,payload.contract_id,user.id,payload.objective,payload.due_at)).id),"case_number":x.case_number,"contract_id":str(x.contract_id),"status":x.status,"due_at":x.due_at.isoformat() if x.due_at else None,"objective":x.objective,"evidence_snapshot":x.evidence_snapshot}}))
    except ValueError as e:raise err(e)
@router.patch("/{case_id}")
def patch_case(case_id:UUID,payload:CaseUpdate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return __import__("json").loads(__import__("json").dumps({**{"id":str((x:=update_case(db,facility_id,case_id,user.id,**payload.model_dump())).id),"case_number":x.case_number,"contract_id":str(x.contract_id),"status":x.status,"owner_id":str(x.owner_id) if x.owner_id else None,"due_at":x.due_at.isoformat() if x.due_at else None,"objective":x.objective,"opening_position":x.opening_position,"target_position":x.target_position,"proposed_terms":x.proposed_terms,"accepted_terms":x.accepted_terms,"notes":x.notes}}))
    except ValueError as e:raise err(e)
@router.get("/{case_id}/items")
def get_items(case_id:UUID,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return [item_out(x) for x in items(db,facility_id,case_id)]
@router.post("/{case_id}/items")
def post_item(case_id:UUID,payload:ItemCreate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return item_out(add_item(db,facility_id,case_id,user.id,**payload.model_dump()))
    except ValueError as e:raise err(e)
@router.patch("/items/{item_id}")
def patch_item(item_id:UUID,payload:ItemUpdate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:return item_out(update_item(db,facility_id,item_id,user.id,**payload.model_dump()))
    except ValueError as e:raise err(e)
@router.get("/{case_id}/events")
def get_events(case_id:UUID,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return [event_out(x) for x in events(db,facility_id,case_id)]
