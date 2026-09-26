from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.dependencies import require_permission
from app.database import get_db
from app.eligibility.schemas import EligibilityRequest, EligibilityResponse
from app.eligibility.service import evaluate
from app.rbac.models import User
router=APIRouter(prefix="/api/v1/eligibility",tags=["Multi-Payer Eligibility"])
@router.post("/evaluate",response_model=EligibilityResponse)
def evaluate_eligibility(payload:EligibilityRequest,db:Session=Depends(get_db),user:User=Depends(require_permission("coverage.read"))):
    try: row,ev=evaluate(db,payload,user.id)
    except Exception as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
    return EligibilityResponse(decision=row.decision,reason_code=row.reason_code,person_id=row.person_id,payer_id=row.payer_id,payer_plan_id=row.payer_plan_id,coverage_id=row.coverage_id,estimated_payer_amount=row.estimated_payer_amount,estimated_patient_amount=row.estimated_patient_amount,evaluated_at=row.evaluated_at.isoformat(),evidence=ev)
