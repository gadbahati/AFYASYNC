from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.patients.models import PatientFacility
from app.maternity.models import Pregnancy, AntenatalVisit, Delivery, Newborn


def _patient_ok(db, patient_id, facility_id):
    return db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id==patient_id, PatientFacility.facility_id==facility_id, PatientFacility.status=="ACTIVE")) is not None

def create_pregnancy(db: Session, facility_id: UUID, actor: UUID, payload):
    if not _patient_ok(db,payload.patient_id,facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    existing=db.scalar(select(Pregnancy.id).where(Pregnancy.patient_id==payload.patient_id,Pregnancy.facility_id==facility_id,Pregnancy.status=="ACTIVE"))
    if existing: raise ValueError("ACTIVE_PREGNANCY_EXISTS")
    item=Pregnancy(facility_id=facility_id,**payload.model_dump()); db.add(item)
    record_audit(db,action="PREGNANCY_REGISTERED",resource_type="Pregnancy",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=payload.patient_id,commit=False)
    db.commit();db.refresh(item);return item

def add_antenatal_visit(db,facility_id,actor,pregnancy_id,payload):
    pregnancy=db.scalar(select(Pregnancy).where(Pregnancy.id==pregnancy_id,Pregnancy.facility_id==facility_id,Pregnancy.status=="ACTIVE"))
    if not pregnancy: raise ValueError("PREGNANCY_NOT_FOUND")
    item=AntenatalVisit(pregnancy_id=pregnancy_id,patient_id=pregnancy.patient_id,facility_id=facility_id,clinician_id=actor,**payload.model_dump());db.add(item)
    record_audit(db,action="ANTENATAL_VISIT_RECORDED",resource_type="AntenatalVisit",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=pregnancy.patient_id,commit=False)
    db.commit();db.refresh(item);return item

def record_delivery(db,facility_id,actor,pregnancy_id,payload):
    pregnancy=db.scalar(select(Pregnancy).where(Pregnancy.id==pregnancy_id,Pregnancy.facility_id==facility_id,Pregnancy.status=="ACTIVE").with_for_update())
    if not pregnancy: raise ValueError("PREGNANCY_NOT_FOUND")
    item=Delivery(pregnancy_id=pregnancy_id,mother_id=pregnancy.patient_id,facility_id=facility_id,recorded_by=actor,**payload.model_dump());db.add(item);pregnancy.status="DELIVERED"
    record_audit(db,action="DELIVERY_RECORDED",resource_type="Delivery",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=pregnancy.patient_id,commit=False)
    db.commit();db.refresh(item);return item

def register_newborn(db,facility_id,actor,delivery_id,payload):
    delivery=db.scalar(select(Delivery).where(Delivery.id==delivery_id,Delivery.facility_id==facility_id))
    if not delivery: raise ValueError("DELIVERY_NOT_FOUND")
    item=Newborn(delivery_id=delivery_id,mother_id=delivery.mother_id,facility_id=facility_id,**payload.model_dump());db.add(item)
    record_audit(db,action="NEWBORN_RECORDED",resource_type="Newborn",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=delivery.mother_id,commit=False)
    db.commit();db.refresh(item);return item
