from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.cash_closure_service import verify_cash_closure

router=APIRouter(prefix="/api/v1/cash-closure",tags=["Cash Closure Verification"])

@router.post("/verify")
def verify(limit:int=Query(200,ge=1,le=500),db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return verify_cash_closure(db,facility_id,user.id,limit)
