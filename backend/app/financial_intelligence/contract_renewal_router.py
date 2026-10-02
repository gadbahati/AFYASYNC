from uuid import UUID
from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.contract_renewal import contract_renewal_intelligence
router=APIRouter(prefix="/api/v1/contract-renewal",tags=["Contract Renewal Intelligence"])
@router.get("")
def renewal(days:int=Query(180,ge=30,le=730),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):return contract_renewal_intelligence(db,facility_id,days)
