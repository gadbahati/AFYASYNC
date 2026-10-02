from datetime import datetime,timezone
from uuid import UUID,uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.claim_clearinghouse.models import ClearinghouseCase
from app.financial_intelligence.resolution_models import RevenueResolutionCase
from app.financial_intelligence.appeal_models import DenialAppeal,DenialAppealEvent
STATUSES={"DRAFT","READY","SUBMITTED","UNDER_REVIEW","APPROVED","PARTIALLY_APPROVED","UPHELD","WITHDRAWN","CLOSED"}
def _number():return f"APL-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:10].upper()}"
def _event(db,a,event,actor=None,to=None,note=None):
    db.add(DenialAppealEvent(appeal_id=a.id,event_type=event,from_status=a.status,to_status=to,actor_id=actor,note=note))
    if to:a.status=to
def create_appeal(db,facility_id,clearinghouse_case_id,actor_id=None,due_at=None,grounds=None):
    c=db.get(ClearinghouseCase,clearinghouse_case_id)
    if c is None:raise ValueError("CLEARINGHOUSE_CASE_NOT_FOUND")
    if c.facility_id!=facility_id:raise ValueError("FACILITY_ACCESS_DENIED")
    if c.status!="REJECTED":raise ValueError("CASE_NOT_DENIED")
    existing=db.scalar(select(DenialAppeal).where(DenialAppeal.facility_id==facility_id,DenialAppeal.clearinghouse_case_id==c.id,DenialAppeal.status.notin_({"CLOSED","WITHDRAWN","UPHELD"})))
    if existing:return existing
    resolution=db.scalar(select(RevenueResolutionCase).where(RevenueResolutionCase.facility_id==facility_id,RevenueResolutionCase.source_type=="DENIAL",RevenueResolutionCase.source_id==c.id))
    a=DenialAppeal(facility_id=facility_id,clearinghouse_case_id=c.id,resolution_case_id=resolution.id if resolution else None,appeal_number=_number(),due_at=due_at,grounds=grounds,evidence_checklist={"clinical_documentation":False,"authorization":False,"eligibility":False,"coding_review":False,"invoice_support":False,"payer_response":True})
    db.add(a);db.flush();_event(db,a,"APPEAL_CREATED",actor_id,note="Appeal workspace created")
    record_audit(db,action="CREATE_DENIAL_APPEAL",resource_type="DENIAL_APPEAL",resource_id=str(a.id),result="SUCCESS",user_id=actor_id,facility_id=facility_id,metadata={"case_id":str(c.id)},commit=False)
    db.commit();db.refresh(a);return a
def update_appeal(db,facility_id,appeal_id,status=None,assigned_to=None,due_at=None,grounds=None,evidence_checklist=None,submission_notes=None,external_reference=None,outcome=None,outcome_notes=None,actor_id=None):
    a=db.get(DenialAppeal,appeal_id)
    if a is None:raise ValueError("APPEAL_NOT_FOUND")
    if a.facility_id!=facility_id:raise ValueError("FACILITY_ACCESS_DENIED")
    if status and status not in STATUSES:raise ValueError("INVALID_APPEAL_STATUS")
    if assigned_to is not None:a.assigned_to=assigned_to
    if due_at is not None:a.due_at=due_at
    if grounds is not None:a.grounds=grounds
    if evidence_checklist is not None:a.evidence_checklist=evidence_checklist
    if submission_notes is not None:a.submission_notes=submission_notes
    if external_reference is not None:a.external_reference=external_reference
    if outcome is not None:a.outcome=outcome
    if outcome_notes is not None:a.outcome_notes=outcome_notes
    now=datetime.now(timezone.utc)
    if status=="SUBMITTED":a.submitted_at=a.submitted_at or now
    if status in {"APPROVED","PARTIALLY_APPROVED","UPHELD","WITHDRAWN","CLOSED"}:a.resolved_at=a.resolved_at or now
    if status:_event(db,a,"STATUS_CHANGED",actor_id,to=status)
    record_audit(db,action="UPDATE_DENIAL_APPEAL",resource_type="DENIAL_APPEAL",resource_id=str(a.id),result="SUCCESS",user_id=actor_id,facility_id=facility_id,metadata={"status":a.status},commit=False)
    db.commit();db.refresh(a);return a
def list_appeals(db,facility_id,status=None,limit=200):
    q=select(DenialAppeal).where(DenialAppeal.facility_id==facility_id)
    if status:q=q.where(DenialAppeal.status==status.upper())
    return list(db.scalars(q.order_by(DenialAppeal.due_at.asc().nullslast(),DenialAppeal.created_at.desc()).limit(min(limit,500))).all())
def overview(db,facility_id):
    appeals=list_appeals(db,facility_id)
    now=datetime.now(timezone.utc)
    due=sum(1 for a in appeals if a.due_at and a.due_at<now and a.status not in {"CLOSED","WITHDRAWN","UPHELD","APPROVED","PARTIALLY_APPROVED"})
    return {"total":len(appeals),"open":sum(a.status not in {"CLOSED","WITHDRAWN","UPHELD","APPROVED","PARTIALLY_APPROVED"} for a in appeals),"overdue":due,"submitted":sum(a.status=="SUBMITTED" for a in appeals),"resolved":sum(a.status in {"APPROVED","PARTIALLY_APPROVED","UPHELD","WITHDRAWN","CLOSED"} for a in appeals)}
def events(db,facility_id,appeal_id):
    a=db.get(DenialAppeal,appeal_id)
    if a is None:raise ValueError("APPEAL_NOT_FOUND")
    if a.facility_id!=facility_id:raise ValueError("FACILITY_ACCESS_DENIED")
    return list(db.scalars(select(DenialAppealEvent).where(DenialAppealEvent.appeal_id==appeal_id).order_by(DenialAppealEvent.created_at.asc())).all())
