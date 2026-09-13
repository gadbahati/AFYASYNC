from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.dependencies import get_db, require_permission
from app.patient_safety.schemas import SafetyIncidentCreate, SafetyIncidentUpdate, SafetyIncidentResponse
from app.patient_safety.service import create_incident, update_incident
router=APIRouter(prefix="/api/v1/patient-safety",tags=["Patient Safety"])
def err(exc):
    codes={"PATIENT_NOT_IN_FACILITY":403,"INCIDENT_NOT_FOUND":404,"INVALID_SEVERITY":422,"INVALID_EVENT_TYPE":422,"INVALID_STATUS":422}
    return HTTPException(status_code=codes.get(str(exc),400),detail=str(exc))
@router.post("/incidents",response_model=SafetyIncidentResponse,status_code=201)
def report(payload:SafetyIncidentCreate,db:Session=Depends(get_db),u=Depends(require_permission("patient_safety.write"))):
    try:return create_incident(db,u.facility_id,u.id,payload)
    except ValueError as exc:raise err(exc)
@router.patch("/incidents/{incident_id}",response_model=SafetyIncidentResponse)
def update(incident_id:UUID,payload:SafetyIncidentUpdate,db:Session=Depends(get_db),u=Depends(require_permission("patient_safety.manage"))):
    try:return update_incident(db,u.facility_id,u.id,incident_id,payload)
    except ValueError as exc:raise err(exc)
