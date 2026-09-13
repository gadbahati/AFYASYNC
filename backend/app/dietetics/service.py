from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.patients.models import PatientFacility
from app.dietetics.models import NutritionAssessment, DietOrder

def _ok(db, patient_id, facility_id):
    return db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id==patient_id,PatientFacility.facility_id==facility_id,PatientFacility.status=="ACTIVE")) is not None

def assess_nutrition(db:Session,facility_id:UUID,actor:UUID,payload):
    if not _ok(db,payload.patient_id,facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    item=NutritionAssessment(facility_id=facility_id,assessed_by=actor,**payload.model_dump());db.add(item)
    record_audit(db,action="NUTRITION_ASSESSED",resource_type="NutritionAssessment",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=payload.patient_id,commit=False)
    db.commit();db.refresh(item);return item

def order_diet(db:Session,facility_id:UUID,actor:UUID,payload):
    if not _ok(db,payload.patient_id,facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    item=DietOrder(facility_id=facility_id,ordered_by=actor,**payload.model_dump());db.add(item)
    record_audit(db,action="DIET_ORDER_CREATED",resource_type="DietOrder",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=facility_id,patient_id=payload.patient_id,commit=False)
    db.commit();db.refresh(item);return item
