from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.claim_clearinghouse.models import ClearinghouseCase
from app.settlement.recovery import RevenueRecoveryCase
from app.revenue_anomaly.models import RevenueAnomalyCase
from app.financial_intelligence.work_queue import CollectionWorkItem

STATUSES={"OPEN","IN_REVIEW","WAITING_EXTERNAL","ESCALATED","RESOLVED","CLOSED"}
PRIORITIES={"LOW","MEDIUM","HIGH","CRITICAL"}
ACTIVE={"OPEN","IN_REVIEW","WAITING_EXTERNAL","ESCALATED"}

def _number(): return f"RR-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:10].upper()}"
def _due(priority): return datetime.now(timezone.utc)+timedelta(days=1 if priority=="CRITICAL" else 3 if priority=="HIGH" else 7 if priority=="MEDIUM" else 14)

def _event(db,case,event_type,actor_id=None,to_status=None,note=None,metadata=None):
    db.add(RevenueResolutionEvent(case_id=case.id,event_type=event_type,from_status=case.status,to_status=to_status,actor_id=actor_id,note=note,metadata_json=metadata))
    if to_status: case.status=to_status

def sync_resolution_queue(db:Session,facility_id:UUID,actor_id:UUID,limit:int=200):
    candidates=[]
    for x in db.scalars(select(ClearinghouseCase).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.status=="REJECTED").order_by(ClearinghouseCase.updated_at.desc()).limit(limit)).all():
        candidates.append(("DENIAL",x.id,x.claim_id,x.payer_id,x.patient_id,x.denial_category or "OTHER",x.claim_amount-x.paid_amount,"Denial requires payer/claims resolution", "HIGH"))
    for x in db.scalars(select(RevenueRecoveryCase).where(RevenueRecoveryCase.facility_id==facility_id,RevenueRecoveryCase.status.notin_(["RECOVERED","CLOSED"])).order_by(RevenueRecoveryCase.updated_at.desc()).limit(limit)).all():
        candidates.append(("RECOVERY",x.id,x.claim_id,x.payer_id,None,x.reason,x.outstanding_amount,"Recover outstanding settlement variance",x.priority if x.priority in PRIORITIES else "MEDIUM"))
    for x in db.scalars(select(RevenueAnomalyCase).where(RevenueAnomalyCase.facility_id==facility_id,RevenueAnomalyCase.status.in_(["OPEN","IN_REVIEW"])).order_by(RevenueAnomalyCase.updated_at.desc()).limit(limit)).all():
        candidates.append(("ANOMALY",x.id,x.claim_id,x.payer_id,x.patient_id,x.anomaly_type,x.amount_at_risk,"Investigate revenue anomaly signal",x.severity if x.severity in PRIORITIES else "MEDIUM"))
    for x in db.scalars(select(CollectionWorkItem).where(CollectionWorkItem.facility_id==facility_id,CollectionWorkItem.status.in_(["OPEN","IN_PROGRESS","SNOOZED"])).order_by(CollectionWorkItem.updated_at.desc()).limit(limit)).all():
        candidates.append(("COLLECTION",x.id,None,None,None,x.source_type,x.outstanding_amount,x.note or "Follow up collection work",x.priority if x.priority in PRIORITIES else "MEDIUM"))
    created=0
    for source_type,source_id,claim_id,payer_id,patient_id,root,amount,action,priority in candidates:
        case=db.scalar(select(RevenueResolutionCase).where(RevenueResolutionCase.facility_id==facility_id,RevenueResolutionCase.source_type==source_type,RevenueResolutionCase.source_id==source_id,RevenueResolutionCase.status.in_(ACTIVE)))
        if case:
            case.amount_at_risk=max(Decimal(str(case.amount_at_risk or 0)),Decimal(str(amount or 0))); case.priority=priority; continue
        case=RevenueResolutionCase(case_number=_number(),facility_id=facility_id,source_type=source_type,source_id=source_id,claim_id=claim_id,payer_id=payer_id,patient_id=patient_id,title=f"{source_type.title()} resolution: {root}",priority=priority,status="OPEN",due_at=_due(priority),amount_at_risk=amount or 0,root_cause=root,resolution_action=action)
        db.add(case);db.flush();_event(db,case,"CASE_CREATED",actor_id,metadata={"source_type":source_type});created+=1
    record_audit(db,action="SYNC_REVENUE_RESOLUTION",resource_type="REVENUE_RESOLUTION_QUEUE",resource_id=str(facility_id),result="SUCCESS",user_id=actor_id,facility_id=facility_id,metadata={"created":created,"candidates":len(candidates)},commit=False)
    db.commit(); return {"created":created,"candidates":len(candidates)}

def list_resolution(db,facility_id,status=None,limit=200):
    q=select(RevenueResolutionCase).where(RevenueResolutionCase.facility_id==facility_id)
    if status:q=q.where(RevenueResolutionCase.status==status.upper())
    return list(db.scalars(q.order_by(RevenueResolutionCase.priority.desc(),RevenueResolutionCase.due_at.asc()).limit(max(1,min(limit,500))).all()))

def overview(db,facility_id):
    rows=db.execute(select(RevenueResolutionCase.status,func.count(RevenueResolutionCase.id),func.coalesce(func.sum(RevenueResolutionCase.amount_at_risk),0)).where(RevenueResolutionCase.facility_id==facility_id).group_by(RevenueResolutionCase.status)).all()
    priorities=db.execute(select(RevenueResolutionCase.priority,func.count(RevenueResolutionCase.id)).where(RevenueResolutionCase.facility_id==facility_id,RevenueResolutionCase.status.in_(ACTIVE)).group_by(RevenueResolutionCase.priority)).all()
    return {"statuses":{str(s):{"count":int(c),"amount_at_risk":float(a or 0)} for s,c,a in rows},"active_priorities":{str(p):int(c) for p,c in priorities}}

def update_resolution(db,facility_id,case_id,status,assigned_to,due_at,root_cause,resolution_action,notes,actor_id):
    case=db.get(RevenueResolutionCase,case_id)
    if case is None:raise ValueError("RESOLUTION_CASE_NOT_FOUND")
    if case.facility_id!=facility_id:raise ValueError("FACILITY_ACCESS_DENIED")
    if status not in STATUSES:raise ValueError("INVALID_RESOLUTION_STATUS")
    if assigned_to is not None:case.assigned_to=assigned_to
    if due_at is not None:case.due_at=due_at
    if root_cause is not None:case.root_cause=root_cause
    if resolution_action is not None:case.resolution_action=resolution_action
    if notes is not None:case.notes=notes
    if status in {"RESOLVED","CLOSED"}:case.resolved_at=datetime.now(timezone.utc)
    _event(db,case,"CASE_UPDATED",actor_id,to_status=status,note=notes)
    record_audit(db,action="UPDATE_REVENUE_RESOLUTION",resource_type="REVENUE_RESOLUTION_CASE",resource_id=str(case.id),result="SUCCESS",user_id=actor_id,facility_id=facility_id,metadata={"status":status},commit=False)
    db.commit();db.refresh(case);return case

def events(db,facility_id,case_id):
    case=db.get(RevenueResolutionCase,case_id)
    if case is None:raise ValueError("RESOLUTION_CASE_NOT_FOUND")
    if case.facility_id!=facility_id:raise ValueError("FACILITY_ACCESS_DENIED")
    return list(db.scalars(select(RevenueResolutionEvent).where(RevenueResolutionEvent.case_id==case_id).order_by(RevenueResolutionEvent.created_at.asc())).all())

from app.financial_intelligence.resolution_models import RevenueResolutionCase, RevenueResolutionEvent
