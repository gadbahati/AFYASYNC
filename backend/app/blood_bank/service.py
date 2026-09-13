from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.patients.models import PatientFacility
from app.blood_bank.models import BloodUnit,BloodRequest,Crossmatch,Transfusion,TransfusionReaction

def _ok(db,pid,fid): return db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id==pid,PatientFacility.facility_id==fid,PatientFacility.status=="ACTIVE")) is not None

def add_unit(db,fid,actor,p):
    item=BloodUnit(facility_id=fid,**p.model_dump());db.add(item);record_audit(db,action="BLOOD_UNIT_REGISTERED",resource_type="BloodUnit",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=fid,commit=False);db.commit();db.refresh(item);return item

def request_blood(db,fid,actor,p):
    if not _ok(db,p.patient_id,fid): raise ValueError("PATIENT_NOT_IN_FACILITY")
    item=BloodRequest(facility_id=fid,requested_by=actor,**p.model_dump());db.add(item);record_audit(db,action="BLOOD_REQUESTED",resource_type="BloodRequest",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=fid,patient_id=p.patient_id,commit=False);db.commit();db.refresh(item);return item

def crossmatch(db,fid,actor,rid,p):
    req=db.scalar(select(BloodRequest).where(BloodRequest.id==rid,BloodRequest.facility_id==fid).with_for_update());unit=db.scalar(select(BloodUnit).where(BloodUnit.id==p.blood_unit_id,BloodUnit.facility_id==fid).with_for_update())
    if not req or not unit: raise ValueError("BLOOD_RECORD_NOT_FOUND")
    if unit.status!="AVAILABLE": raise ValueError("BLOOD_UNIT_NOT_AVAILABLE")
    item=Crossmatch(request_id=rid,performed_by=actor,**p.model_dump());db.add(item)
    if p.result.upper()=="COMPATIBLE": unit.status="CROSSMATCHED";req.status="MATCHED"
    else: req.status="REJECTED"
    record_audit(db,action="BLOOD_CROSSMATCH_RECORDED",resource_type="Crossmatch",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=fid,commit=False);db.commit();db.refresh(item);return item

def transfuse(db,fid,actor,rid,p):
    req=db.scalar(select(BloodRequest).where(BloodRequest.id==rid,BloodRequest.facility_id==fid).with_for_update());unit=db.scalar(select(BloodUnit).where(BloodUnit.id==p.blood_unit_id,BloodUnit.facility_id==fid).with_for_update())
    if not req or not unit: raise ValueError("BLOOD_RECORD_NOT_FOUND")
    cm=db.scalar(select(Crossmatch).where(Crossmatch.request_id==rid,Crossmatch.blood_unit_id==unit.id,Crossmatch.result=="COMPATIBLE"))
    if not cm: raise ValueError("COMPATIBLE_CROSSMATCH_REQUIRED")
    if unit.status not in ("CROSSMATCHED","AVAILABLE"): raise ValueError("BLOOD_UNIT_NOT_AVAILABLE")
    item=Transfusion(request_id=rid,blood_unit_id=unit.id,patient_id=req.patient_id,administered_by=actor,**p.model_dump());db.add(item);unit.status="TRANSFUSED";req.status="ISSUED"
    record_audit(db,action="TRANSFUSION_STARTED",resource_type="Transfusion",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=fid,patient_id=req.patient_id,commit=False);db.commit();db.refresh(item);return item

def reaction(db,fid,actor,tid,p):
    tr=db.scalar(select(Transfusion).where(Transfusion.id==tid).join(BloodRequest,BloodRequest.id==Transfusion.request_id).where(BloodRequest.facility_id==fid))
    if not tr: raise ValueError("TRANSFUSION_NOT_FOUND")
    item=TransfusionReaction(transfusion_id=tid,reported_by=actor,**p.model_dump());db.add(item);tr.status="REACTION_REPORTED";record_audit(db,action="TRANSFUSION_REACTION_REPORTED",resource_type="TransfusionReaction",result="SUCCESS",user_id=actor,resource_id=str(item.id),facility_id=fid,patient_id=tr.patient_id,commit=False);db.commit();db.refresh(item);return item
