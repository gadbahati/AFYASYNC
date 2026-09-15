from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.patients.models import PatientFacility
from app.child_health.models import ChildHealthRecord, GrowthObservation, Immunisation

def _ok(db, patient_id, facility_id):
    return db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id==patient_id, PatientFacility.facility_id==facility_id, PatientFacility.status=="ACTIVE")) is not None

def list_children(db:Session,facility_id:UUID):
    return list(db.scalars(select(ChildHealthRecord).where(ChildHealthRecord.facility_id==facility_id,ChildHealthRecord.status=="ACTIVE").order_by(ChildHealthRecord.birth_date.desc().nullslast(), ChildHealthRecord.id.desc()).limit(200)).all())

def list_growth(db:Session,facility_id:UUID,child_id:UUID):
    return list(db.scalars(select(GrowthObservation).where(GrowthObservation.facility_id==facility_id,GrowthObservation.child_id==child_id).order_by(GrowthObservation.observed_at.desc()).limit(100)).all())

def list_immunisations(db:Session,facility_id:UUID,child_id:UUID):
    return list(db.scalars(select(Immunisation).where(Immunisation.facility_id==facility_id,Immunisation.child_id==child_id).order_by(Immunisation.administered_at.desc()).limit(100)).all())

def create_child(db:Session,facility_id:UUID,actor:UUID,payload):
    if not _ok(db,payload.patient_id,facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    item=ChildHealthRecord(facility_id=facility_id,**payload.model_dump());db.add(item)
    record_audit(db,action="CHILD_HEALTH_REGISTERED",resource_type="ChildHealthRecord",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=payload.patient_id,commit=False)
    db.commit();db.refresh(item);return item

def add_growth(db,facility_id,actor,child_id,payload):
    child=db.scalar(select(ChildHealthRecord).where(ChildHealthRecord.id==child_id,ChildHealthRecord.facility_id==facility_id,ChildHealthRecord.status=="ACTIVE"))
    if not child: raise ValueError("CHILD_RECORD_NOT_FOUND")
    item=GrowthObservation(child_id=child_id,facility_id=facility_id,recorded_by=actor,**payload.model_dump());db.add(item)
    record_audit(db,action="CHILD_GROWTH_RECORDED",resource_type="GrowthObservation",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=child.patient_id,commit=False)
    db.commit();db.refresh(item);return item

def add_immunisation(db,facility_id,actor,child_id,payload):
    child=db.scalar(select(ChildHealthRecord).where(ChildHealthRecord.id==child_id,ChildHealthRecord.facility_id==facility_id,ChildHealthRecord.status=="ACTIVE"))
    if not child: raise ValueError("CHILD_RECORD_NOT_FOUND")
    item=Immunisation(child_id=child_id,facility_id=facility_id,recorded_by=actor,**payload.model_dump());db.add(item)
    record_audit(db,action="CHILD_IMMUNISATION_RECORDED",resource_type="Immunisation",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=child.patient_id,commit=False)
    db.commit();db.refresh(item);return item
