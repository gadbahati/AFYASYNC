from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.patients.models import PatientFacility
from app.patient_safety.models import SafetyIncident

VALID_SEVERITY={"LOW","MODERATE","SEVERE","CRITICAL"}
VALID_EVENT_TYPES={"INCIDENT","NEAR_MISS","UNSAFE_CONDITION"}
VALID_STATUS={"OPEN","UNDER_REVIEW","ACTION_REQUIRED","CLOSED"}

def _patient_ok(db, patient_id, facility_id):
    return db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id==patient_id,PatientFacility.facility_id==facility_id,PatientFacility.status=="ACTIVE")) is not None

def _number(db):
    year=datetime.now(timezone.utc).year
    count=db.scalar(select(SafetyIncident.id).where(SafetyIncident.incident_number.like(f"PS-{year}-%")).order_by(SafetyIncident.created_at.desc()).limit(1))
    if count is None: return f"PS-{year}-000001"
    last=db.scalar(select(SafetyIncident.incident_number).order_by(SafetyIncident.created_at.desc()).limit(1))
    try: return f"PS-{year}-{int(last.rsplit('-',1)[1])+1:06d}"
    except (ValueError,IndexError): return f"PS-{year}-{datetime.now(timezone.utc).microsecond:06d}"

def create_incident(db:Session,facility_id:UUID,actor:UUID,payload):
    if payload.patient_id and not _patient_ok(db,payload.patient_id,facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    if payload.severity not in VALID_SEVERITY: raise ValueError("INVALID_SEVERITY")
    if payload.event_type not in VALID_EVENT_TYPES: raise ValueError("INVALID_EVENT_TYPE")
    item=SafetyIncident(facility_id=facility_id,reported_by=actor,incident_number=_number(db),**payload.model_dump());db.add(item)
    record_audit(db,action="SAFETY_INCIDENT_REPORTED",resource_type="SafetyIncident",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=payload.patient_id,commit=False)
    db.commit();db.refresh(item);return item

def update_incident(db:Session,facility_id:UUID,actor:UUID,incident_id:UUID,payload):
    item=db.scalar(select(SafetyIncident).where(SafetyIncident.id==incident_id,SafetyIncident.facility_id==facility_id).with_for_update())
    if not item: raise ValueError("INCIDENT_NOT_FOUND")
    data=payload.model_dump(exclude_unset=True)
    if data.get("status") and data["status"] not in VALID_STATUS: raise ValueError("INVALID_STATUS")
    for key,value in data.items(): setattr(item,key,value)
    if item.status=="CLOSED": item.closed_at=datetime.now(timezone.utc);item.closed_by=actor
    record_audit(db,action="SAFETY_INCIDENT_UPDATED",resource_type="SafetyIncident",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=item.patient_id,commit=False)
    db.commit();db.refresh(item);return item
