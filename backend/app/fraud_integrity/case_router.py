from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.fraud_integrity.case_service import create_case, list_cases, resolve_case, FraudCaseError

router=APIRouter(prefix="/api/v1/fraud-integrity/cases",tags=["Fraud Integrity Cases"])

class CaseCreate(BaseModel):
    signal: dict
class CaseResolve(BaseModel):
    status: str
    note: str = Field(min_length=1,max_length=2000)

@router.get("")
def cases(status: str|None=Query(default=None),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("reports.read"))):
    _=user; return list_cases(db,facility_id,status)

@router.post("")
def case(payload:CaseCreate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("reports.read"))):
    return create_case(db,facility_id=facility_id,actor_user_id=user.id,signal=payload.signal)

@router.patch("/{case_id}")
def resolve(case_id:UUID,payload:CaseResolve,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("reports.read"))):
    try:return resolve_case(db,facility_id=facility_id,case_id=case_id,actor_user_id=user.id,status=payload.status,note=payload.note)
    except FraudCaseError as e: raise HTTPException(status_code=404 if str(e)=="CASE_NOT_FOUND" else 409,detail=str(e))
