from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.work_queue_service import list_work, queue_overview, sync_collection_queue, update_work

router=APIRouter(prefix="/api/v1/collection-work",tags=["Collection Work"])

class WorkUpdate(BaseModel):
    status:str=Field(default="IN_PROGRESS")
    assigned_to:UUID|None=None
    due_at:datetime|None=None
    note:str|None=None

@router.get("/overview")
def overview(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    _=user; return queue_overview(db,facility_id)

@router.get("")
def items(status:str|None=None,limit:int=Query(100,ge=1,le=500),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    _=user
    return [{"id":str(x.id),"facility_id":str(x.facility_id),"source_type":x.source_type,"source_id":str(x.source_id),"title":x.title,"priority":x.priority,"status":x.status,"assigned_to":str(x.assigned_to) if x.assigned_to else None,"due_at":x.due_at.isoformat() if x.due_at else None,"outstanding_amount":float(x.outstanding_amount or 0),"note":x.note,"created_at":x.created_at.isoformat() if x.created_at else None,"updated_at":x.updated_at.isoformat() if x.updated_at else None} for x in list_work(db,facility_id,status,limit)]

@router.post("/sync")
def sync(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return sync_collection_queue(db,facility_id,user.id)

@router.patch("/{item_id}")
def update(item_id:UUID,payload:WorkUpdate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    x=update_work(db,facility_id,item_id,payload.status,payload.assigned_to,payload.due_at,payload.note,user.id)
    return {"id":str(x.id),"status":x.status,"assigned_to":str(x.assigned_to) if x.assigned_to else None,"due_at":x.due_at.isoformat() if x.due_at else None,"note":x.note}
