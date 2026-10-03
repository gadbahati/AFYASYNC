from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.revenue_workflow_service import automate_revenue_actions,orchestrate_revenue_workflow,reconcile_revenue_work

router=APIRouter(prefix="/api/v1/revenue-workflow",tags=["Revenue Workflow Automation"])

@router.post("/orchestrate")
def orchestrate(limit:int=Query(50,ge=1,le=200),db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return orchestrate_revenue_workflow(db,facility_id,user.id,limit)

@router.post("/reconcile")
def reconcile(limit:int=Query(200,ge=1,le=500),db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return reconcile_revenue_work(db,facility_id,user.id,limit)

@router.post("/automate")
def automate(limit:int=Query(50,ge=1,le=200),db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    return automate_revenue_actions(db,facility_id,user.id,limit)
