from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.patients.models import PatientFacility
from app.infection_control.models import InfectionIncident, IsolationPrecaution

def _patient_ok(db, patient_id, facility_id):
    return db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id==patient_id, PatientFacility.facility_id==facility_id, PatientFacility.status=="ACTIVE")) is not None

def report_incident(db:Session,facility_id:UUID,actor:UUID,payload):
    if payload.patient_id and not _patient_ok(db,payload.patient_id,facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    item=InfectionIncident(facility_id=facility_id,reported_by=actor,**payload.model_dump());db.add(item)
    record_audit(db,action="INFECTION_INCIDENT_REPORTED",resource_type="InfectionIncident",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=payload.patient_id,commit=False)
    db.commit();db.refresh(item);return item

def start_isolation(db:Session,facility_id:UUID,actor:UUID,payload):
    if not _patient_ok(db,payload.patient_id,facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    active=db.scalar(select(IsolationPrecaution.id).where(IsolationPrecaution.patient_id==payload.patient_id,IsolationPrecaution.facility_id==facility_id,IsolationPrecaution.status=="ACTIVE"))
    if active: raise ValueError("ACTIVE_ISOLATION_EXISTS")
    item=IsolationPrecaution(facility_id=facility_id,created_by=actor,**payload.model_dump());db.add(item)
    record_audit(db,action="ISOLATION_STARTED",resource_type="IsolationPrecaution",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=payload.patient_id,commit=False)
    db.commit();db.refresh(item);return item
