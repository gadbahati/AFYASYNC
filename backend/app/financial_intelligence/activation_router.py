from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.activation_service import activate_contract,overview,events

router=APIRouter(prefix="/api/v1/contract-activation",tags=["Contract Activation"])

class ActivateBody(BaseModel):
    terms:dict|None=None

def err(e): return HTTPException(status_code=409,detail=str(e))

@router.get("/overview")
def get_overview(db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return overview(db,facility_id)

@router.post("/{contract_id}/activate")
def activate(contract_id:UUID,payload:ActivateBody,db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try: return activate_contract(db,facility_id,contract_id,user.id,payload.terms)
    except ValueError as e: raise err(e)

@router.get("/{contract_id}/events")
def get_events(contract_id:UUID,db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    rows=events(db,facility_id,contract_id)
    return [{"id":str(x.id),"event_type":x.event_type,"status":x.status,"actor_id":str(x.actor_id) if x.actor_id else None,"details":x.details,"created_at":x.created_at.isoformat() if x.created_at else None} for x in rows]
