from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session
from app.auth.dependencies import require_national_permission
from app.database import get_db
from app.rbac.models import User
from app.care_coordination.schemas import CoordinationCreate,CoordinationUpdate
from app.care_coordination.service import *
router=APIRouter(prefix="/api/v1/care-coordination",tags=["Care Coordination"])
def err(x): return HTTPException(status_code={"REFERRAL_NOT_FOUND":404,"CASE_NOT_FOUND":404,"COORDINATION_CASE_EXISTS":409,"INVALID_STATUS":400}.get(str(x),400),detail=str(x))
@router.get("/overview")
def get_overview(_:User=Depends(require_national_permission("referral.network.read")),db:Session=Depends(get_db)): return overview(db)
@router.get("/cases")
def get_cases(status:str|None=None,limit:int=Query(100,ge=1,le=200),_:User=Depends(require_national_permission("referral.network.read")),db:Session=Depends(get_db)): return list_cases(db,status,limit)
@router.post("/cases",status_code=201)
def create(body:CoordinationCreate,user:User=Depends(require_national_permission("referral.network.manage")),db:Session=Depends(get_db)):
 try:return create_case(db,body.referral_id,user.id,body.due_at,body.notes)
 except CoordinationError as x:raise err(x) from x
@router.patch("/cases/{case_id}")
def update(case_id:UUID,body:CoordinationUpdate,user:User=Depends(require_national_permission("referral.network.manage")),db:Session=Depends(get_db)):
 try:return update_case(db,case_id,body.model_dump(exclude_none=True),user.id)
 except CoordinationError as x:raise err(x) from x
