from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.cash_closure_command import cash_closure_command, revenue_cash_assurance

router=APIRouter(prefix="/api/v1/cash-closure",tags=["Cash Closure Verification"])

@router.get("/assurance")
def assurance(db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return revenue_cash_assurance(db,facility_id)

@router.get("/command")
def command(limit:int=Query(100,ge=1,le=200),db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return cash_closure_command(db,facility_id,limit)

@router.post("/verify")
def verify(limit:int=Query(200,ge=1,le=500),db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    from app.financial_intelligence.cash_closure_service import verify_cash_closure
    return verify_cash_closure(db,facility_id,user.id,limit)
