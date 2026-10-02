from uuid import UUID
from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.tariff_intelligence import tariff_intelligence
router=APIRouter(prefix="/api/v1/tariff-intelligence",tags=["Tariff Reimbursement Intelligence"])
@router.get("")
def intelligence(days:int=Query(90,ge=1,le=730),limit:int=Query(100,ge=1,le=500),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return tariff_intelligence(db,facility_id,days,limit)
