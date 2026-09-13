from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.patients.models import PatientFacility
from app.blood_bank.models import BloodUnit, BloodRequest, Crossmatch, Transfusion, TransfusionReaction

VALID_GROUPS={"A+","A-","B+","B-","AB+","AB-","O+","O-"}
VALID_COMPONENTS={"WHOLE_BLOOD","RED_CELLS","PLATELETS","PLASMA","CRYOPRECIPITATE"}

def _ok(db,pid,fid):
    return db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id==pid,PatientFacility.facility_id==fid,PatientFacility.status=="ACTIVE")) is not None

def add_unit(db,fid,actor,p):
    if p.blood_group not in VALID_GROUPS: raise ValueError("INVALID_BLOOD_GROUP")
    if p.component not in VALID_COMPONENTS: raise ValueError("INVALID_BLOOD_COMPONENT")
    if p.expires_at and p.collected_at and p.expires_at<=p.collected_at: raise ValueError("INVALID_EXPIRY")
    if p.screening_status.upper() not in {"PENDING","PASSED","FAILED","QUARANTINED"}: raise ValueError("INVALID_SCREENING_STATUS")
    item=BloodUnit(facility_id=fid,**p.model_dump());db.add(item)
    record_audit(db,action="BLOOD_UNIT_REGISTERED",resource_type="BloodUnit",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=fid,commit=False)
    db.commit();db.refresh(item);return item

def request_blood(db,fid,actor,p):
    if not _ok(db,p.patient_id,fid): raise ValueError("PATIENT_NOT_IN_FACILITY")
    if p.blood_group and p.blood_group not in VALID_GROUPS: raise ValueError("INVALID_BLOOD_GROUP")
    if p.component not in VALID_COMPONENTS: raise ValueError("INVALID_BLOOD_COMPONENT")
    item=BloodRequest(facility_id=fid,requested_by=actor,**p.model_dump());db.add(item)
    record_audit(db,action="BLOOD_REQUESTED",resource_type="BloodRequest",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=fid,patient_id=p.patient_id,commit=False)
    db.commit();db.refresh(item);return item

def crossmatch(db,fid,actor,rid,p):
    req=db.scalar(select(BloodRequest).where(BloodRequest.id==rid,BloodRequest.facility_id==fid).with_for_update())
    unit=db.scalar(select(BloodUnit).where(BloodUnit.id==p.blood_unit_id,BloodUnit.facility_id==fid).with_for_update())
    if not req or not unit: raise ValueError("BLOOD_RECORD_NOT_FOUND")
    if p.patient_blood_group not in VALID_GROUPS: raise ValueError("INVALID_BLOOD_GROUP")
    if unit.status!="AVAILABLE": raise ValueError("BLOOD_UNIT_NOT_AVAILABLE")
    if unit.screening_status!="PASSED": raise ValueError("BLOOD_UNIT_NOT_RELEASED")
    if unit.expires_at and unit.expires_at<=__import__("datetime").datetime.now(__import__("datetime").timezone.utc): raise ValueError("BLOOD_UNIT_EXPIRED")
    if req.blood_group and req.blood_group!=p.patient_blood_group: raise ValueError("PATIENT_GROUP_MISMATCH")
    item=Crossmatch(request_id=rid,performed_by=actor,**p.model_dump());db.add(item)
    if p.result.upper()=="COMPATIBLE": unit.status="CROSSMATCHED";req.status="MATCHED"
    else: req.status="REJECTED"
    record_audit(db,action="BLOOD_CROSSMATCH_RECORDED",resource_type="Crossmatch",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=fid,patient_id=req.patient_id,commit=False)
    db.commit();db.refresh(item);return item

def transfuse(db,fid,actor,rid,p):
    req=db.scalar(select(BloodRequest).where(BloodRequest.id==rid,BloodRequest.facility_id==fid).with_for_update())
    unit=db.scalar(select(BloodUnit).where(BloodUnit.id==p.blood_unit_id,BloodUnit.facility_id==fid).with_for_update())
    if not req or not unit: raise ValueError("BLOOD_RECORD_NOT_FOUND")
    cm=db.scalar(select(Crossmatch).where(Crossmatch.request_id==rid,Crossmatch.blood_unit_id==unit.id,Crossmatch.result=="COMPATIBLE"))
    if not cm: raise ValueError("COMPATIBLE_CROSSMATCH_REQUIRED")
    if unit.screening_status!="PASSED": raise ValueError("BLOOD_UNIT_NOT_RELEASED")
    if unit.status!="CROSSMATCHED": raise ValueError("BLOOD_UNIT_NOT_CROSSMATCHED")
    item=Transfusion(request_id=rid,blood_unit_id=unit.id,patient_id=req.patient_id,administered_by=actor,**p.model_dump());db.add(item);unit.status="TRANSFUSED";req.status="ISSUED"
    record_audit(db,action="TRANSFUSION_STARTED",resource_type="Transfusion",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=fid,patient_id=req.patient_id,commit=False)
    db.commit();db.refresh(item);return item

def reaction(db,fid,actor,tid,p):
    tr=db.scalar(select(Transfusion).where(Transfusion.id==tid).join(BloodRequest,BloodRequest.id==Transfusion.request_id).where(BloodRequest.facility_id==fid))
    if not tr: raise ValueError("TRANSFUSION_NOT_FOUND")
    item=TransfusionReaction(transfusion_id=tid,reported_by=actor,**p.model_dump());db.add(item);tr.status="REACTION_REPORTED"
    record_audit(db,action="TRANSFUSION_REACTION_REPORTED",resource_type="TransfusionReaction",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=fid,patient_id=tr.patient_id,commit=False)
    db.commit();db.refresh(item);return item
