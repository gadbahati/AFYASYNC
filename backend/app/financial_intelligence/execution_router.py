from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context,require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.execution_service import request_execution,review_execution,execute_contract,overview
router=APIRouter(prefix="/api/v1/contract-execution",tags=["Contract Execution"])
class RequestBody(BaseModel):
    contract_id:UUID
    negotiation_case_id:UUID|None=None
    terms:dict|None=None
    notes:str|None=None
class ReviewBody(BaseModel):
    status:str
    notes:str|None=None
class ExecuteBody(BaseModel):
    execution_reference:str|None=None
    terms:dict|None=None
    notes:str|None=None
def err(e): return HTTPException(status_code=409,detail=str(e))
@router.get("/overview")
def get_overview(db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))): return overview(db,facility_id)
@router.post("/request")
def create_request(payload:RequestBody,db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:
        a=request_execution(db,facility_id,payload.contract_id,payload.negotiation_case_id,user.id,payload.terms,payload.notes)
        return {"id":str(a.id),"contract_id":str(a.contract_id),"status":a.status,"requested_terms":a.requested_terms}
    except ValueError as e: raise err(e)
@router.patch("/approvals/{approval_id}")
def review(approval_id:UUID,payload:ReviewBody,db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:
        a=review_execution(db,facility_id,approval_id,user.id,payload.status,payload.notes)
        return {"id":str(a.id),"contract_id":str(a.contract_id),"status":a.status}
    except ValueError as e: raise err(e)
@router.post("/{contract_id}/execute")
def execute(contract_id:UUID,payload:ExecuteBody,db:Session=Depends(get_db),facility_id=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:
        c=execute_contract(db,facility_id,contract_id,user.id,payload.execution_reference,payload.terms,payload.notes)
        return {"id":str(c.id),"status":c.status,"execution_status":c.execution_status,"execution_reference":c.execution_reference}
    except ValueError as e: raise err(e)
