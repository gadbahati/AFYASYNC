from datetime import datetime,timezone
from uuid import UUID,uuid4
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.referrals.models import Referral
from app.care_coordination.models import CareCoordinationCase
class CoordinationError(ValueError): pass
VALID={"OPEN","ACCEPTED","SCHEDULED","HANDED_OFF","COMPLETED","CANCELLED","OVERDUE"}
def create_case(db:Session,referral_id:UUID,actor:UUID,due_at=None,notes=None):
 r=db.get(Referral,referral_id)
 if not r: raise CoordinationError("REFERRAL_NOT_FOUND")
 existing=db.scalar(select(CareCoordinationCase).where(CareCoordinationCase.referral_id==referral_id))
 if existing: raise CoordinationError("COORDINATION_CASE_EXISTS")
 row=CareCoordinationCase(case_number=f"CARE-{uuid4().hex[:18].upper()}",referral_id=r.id,patient_id=r.patient_id,source_facility_id=r.source_facility_id,destination_facility_id=r.destination_facility_id,due_at=due_at,notes=notes,created_by=actor)
 db.add(row);db.flush()
 record_audit(db,action="CREATE_CARE_COORDINATION_CASE",resource_type="CARE_COORDINATION",resource_id=str(row.id),result="SUCCESS",user_id=actor,patient_id=row.patient_id,metadata={"referral_id":str(r.id)},commit=False)
 db.commit();db.refresh(row);return row
def list_cases(db:Session,status=None,limit=100):
 q=select(CareCoordinationCase).order_by(CareCoordinationCase.created_at.desc()).limit(min(max(limit,1),200))
 if status:q=q.where(CareCoordinationCase.status==status)
 return list(db.scalars(q))
def update_case(db:Session,case_id:UUID,payload:dict,actor:UUID):
 row=db.get(CareCoordinationCase,case_id)
 if not row: raise CoordinationError("CASE_NOT_FOUND")
 new=payload.get("status")
 if new and new not in VALID: raise CoordinationError("INVALID_STATUS")
 if new=="ACCEPTED" and row.accepted_at is None: row.accepted_at=datetime.now(timezone.utc)
 if new=="HANDED_OFF" and row.handoff_at is None: row.handoff_at=datetime.now(timezone.utc)
 if new in {"COMPLETED","CANCELLED"} and row.closed_at is None: row.closed_at=datetime.now(timezone.utc)
 if new: row.status=new
 for k in ("appointment_at","outcome","notes","evidence"):
  if k in payload and payload[k] is not None:setattr(row,k,payload[k])
 record_audit(db,action="UPDATE_CARE_COORDINATION_CASE",resource_type="CARE_COORDINATION",resource_id=str(row.id),result="SUCCESS",user_id=actor,patient_id=row.patient_id,metadata={"status":row.status},commit=False)
 db.commit();db.refresh(row);return row
def overview(db:Session):
 total=db.scalar(select(func.count()).select_from(CareCoordinationCase)) or 0
 open_count=db.scalar(select(func.count()).select_from(CareCoordinationCase).where(CareCoordinationCase.status.in_([ "OPEN","ACCEPTED","SCHEDULED","HANDED_OFF","OVERDUE"]))) or 0
 overdue=db.scalar(select(func.count()).select_from(CareCoordinationCase).where(CareCoordinationCase.due_at < datetime.now(timezone.utc),CareCoordinationCase.status.in_([ "OPEN","ACCEPTED","SCHEDULED","HANDED_OFF"]))) or 0
 completed=db.scalar(select(func.count()).select_from(CareCoordinationCase).where(CareCoordinationCase.status=="COMPLETED")) or 0
 return {"total":int(total),"open":int(open_count),"overdue":int(overdue),"completed":int(completed)}
