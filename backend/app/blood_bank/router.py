from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.auth.dependencies import get_db,require_permission
from app.blood_bank.schemas import *
from app.blood_bank.service import add_unit,request_blood,crossmatch,transfuse,reaction
router=APIRouter(prefix="/api/v1/blood-bank",tags=["Blood Bank & Transfusion"])
def e(x): return HTTPException({"PATIENT_NOT_IN_FACILITY":403,"BLOOD_RECORD_NOT_FOUND":404,"TRANSFUSION_NOT_FOUND":404}.get(str(x),400),detail=str(x))
@router.post("/units",response_model=BloodUnitResponse,status_code=201)
def unit(p:BloodUnitCreate,db:Session=Depends(get_db),u=Depends(require_permission("lab.catalogue.write"))):
 try:return add_unit(db,u.facility_id,u.id,p)
 except ValueError as x:raise e(x)
@router.post("/requests",response_model=BloodRequestResponse,status_code=201)
def request(p:BloodRequestCreate,db:Session=Depends(get_db),u=Depends(require_permission("encounters.create"))):
 try:return request_blood(db,u.facility_id,u.id,p)
 except ValueError as x:raise e(x)
@router.post("/requests/{request_id}/crossmatch",status_code=201)
def match(request_id:UUID,p:CrossmatchCreate,db:Session=Depends(get_db),u=Depends(require_permission("lab.catalogue.write"))):
 try:return crossmatch(db,u.facility_id,u.id,request_id,p)
 except ValueError as x:raise e(x)
@router.post("/requests/{request_id}/transfuse",status_code=201)
def give(request_id:UUID,p:TransfusionCreate,db:Session=Depends(get_db),u=Depends(require_permission("encounters.create"))):
 try:return transfuse(db,u.facility_id,u.id,request_id,p)
 except ValueError as x:raise e(x)
@router.post("/transfusions/{transfusion_id}/reaction",status_code=201)
def report(transfusion_id:UUID,p:ReactionCreate,db:Session=Depends(get_db),u=Depends(require_permission("encounters.create"))):
 try:return reaction(db,u.facility_id,u.id,transfusion_id,p)
 except ValueError as x:raise e(x)
