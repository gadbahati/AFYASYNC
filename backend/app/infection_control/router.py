from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.auth.dependencies import get_db,require_permission
from app.infection_control.schemas import *
from app.infection_control.service import report_incident,start_isolation
router=APIRouter(prefix="/api/v1/infection-control",tags=["Infection Prevention & Control"])
def err(e): return HTTPException({"PATIENT_NOT_IN_FACILITY":403,"ACTIVE_ISOLATION_EXISTS":409}.get(str(e),400),detail=str(e))
@router.post("/incidents",response_model=InfectionIncidentResponse,status_code=201)
def incident(p:InfectionIncidentCreate,db:Session=Depends(get_db),u=Depends(require_permission("encounters.create"))):
 try:return report_incident(db,u.facility_id,u.id,p)
 except ValueError as e:raise err(e)
@router.post("/isolation",response_model=IsolationResponse,status_code=201)
def isolation(p:IsolationCreate,db:Session=Depends(get_db),u=Depends(require_permission("encounters.create"))):
 try:return start_isolation(db,u.facility_id,u.id,p)
 except ValueError as e:raise err(e)
