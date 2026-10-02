from uuid import UUID
from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.payer_command import payer_command,payer_summary
router=APIRouter(prefix="/api/v1/payer-command",tags=["Payer Command Intelligence"])
@router.get("")
def command(days:int=Query(90,ge=1,le=730),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return payer_command(db,facility_id,days)
@router.get("/summary")
def summary(days:int=Query(90,ge=1,le=730),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return payer_summary(db,facility_id,days)
