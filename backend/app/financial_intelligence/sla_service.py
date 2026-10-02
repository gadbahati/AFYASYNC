from datetime import datetime,timedelta,timezone
from decimal import Decimal
from sqlalchemy import select,func,case
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.coverage.models import Payer
from app.claim_clearinghouse.models import ClearinghouseCase
from app.financial_intelligence.resolution_models import RevenueResolutionCase
from app.financial_intelligence.sla_models import PayerSLAPolicy,RevenueResolutionSLAEvent

def _policy(db,facility_id,payer_id):
    if payer_id is None:return None
    return db.scalar(select(PayerSLAPolicy).where(PayerSLAPolicy.facility_id==facility_id,PayerSLAPolicy.payer_id==payer_id,PayerSLAPolicy.active.is_(True)))
def upsert_policy(db,facility_id,payer_id,denial_response_hours=48,resolution_hours=168,appeal_hours=120,escalation_hours=24,notes=None,actor_id=None):
    if any(v<1 or v>8760 for v in [denial_response_hours,resolution_hours,appeal_hours,escalation_hours]):raise ValueError("INVALID_SLA_HOURS")
    if db.get(Payer,payer_id) is None:raise ValueError("PAYER_NOT_FOUND")
    p=db.scalar(select(PayerSLAPolicy).where(PayerSLAPolicy.facility_id==facility_id,PayerSLAPolicy.payer_id==payer_id))
    if p is None:p=PayerSLAPolicy(facility_id=facility_id,payer_id=payer_id);db.add(p)
    p.denial_response_hours=denial_response_hours;p.resolution_hours=resolution_hours;p.appeal_hours=appeal_hours;p.escalation_hours=escalation_hours;p.notes=notes;p.active=True
    record_audit(db,"UPSERT_PAYER_SLA","PAYER_SLA_POLICY",str(payer_id),{"denial_response_hours":denial_response_hours,"resolution_hours":resolution_hours,"appeal_hours":appeal_hours,"escalation_hours":escalation_hours},user_id=actor_id,facility_id=facility_id,commit=False)
    db.commit();db.refresh(p);return p
def list_policies(db,facility_id):
    rows=db.execute(select(PayerSLAPolicy,Payer.name,Payer.code).join(Payer,Payer.id==PayerSLAPolicy.payer_id).where(PayerSLAPolicy.facility_id==facility_id).order_by(Payer.name)).all()
    return [{"id":str(p.id),"payer_id":str(p.payer_id),"payer_name":n,"payer_code":c,"denial_response_hours":p.denial_response_hours,"resolution_hours":p.resolution_hours,"appeal_hours":p.appeal_hours,"escalation_hours":p.escalation_hours,"active":p.active,"notes":p.notes} for p,n,c in rows]
def denial_intelligence(db,facility_id,days=90):
    since=datetime.now(timezone.utc)-timedelta(days=days)
    rows=db.execute(select(ClearinghouseCase.payer_id,ClearinghouseCase.denial_category,func.count(ClearinghouseCase.id),func.coalesce(func.sum(ClearinghouseCase.claim_amount-ClearinghouseCase.paid_amount),0)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.status=="REJECTED",ClearinghouseCase.updated_at>=since).group_by(ClearinghouseCase.payer_id,ClearinghouseCase.denial_category)).all()
    out=[]
    for pid,cat,count,amount in rows:
        p=db.get(Payer,pid) if pid else None
        out.append({"payer_id":str(pid) if pid else None,"payer_name":p.name if p else "Unassigned","payer_code":p.code if p else None,"category":cat or "OTHER","denials":int(count),"amount_at_risk":float(max(Decimal("0"),Decimal(str(amount or 0))))})
    totals={}
    for x in out:
        z=totals.setdefault(x["category"],{"denials":0,"amount_at_risk":0.0});z["denials"]+=x["denials"];z["amount_at_risk"]+=x["amount_at_risk"]
    out.sort(key=lambda x:(-x["denials"],-x["amount_at_risk"]))
    return {"window_days":days,"by_payer_category":out,"by_category":totals}

def sync_sla(db,facility_id,actor_id=None,limit=500):
    now=datetime.now(timezone.utc);initialized=breached=escalated=response_breaches=appeal_risk=0
    cases=db.scalars(select(RevenueResolutionCase).where(RevenueResolutionCase.facility_id==facility_id,RevenueResolutionCase.status.in_({"OPEN","IN_REVIEW","WAITING_EXTERNAL","ESCALATED"})).limit(limit)).all()
    for c in cases:
        p=_policy(db,facility_id,c.payer_id)
        if not p:c.sla_status="NO_POLICY";continue
        if c.sla_due_at is None:
            c.sla_due_at=c.created_at+timedelta(hours=p.resolution_hours)
            c.denial_response_due_at=c.created_at+timedelta(hours=p.denial_response_hours) if c.source_type=="DENIAL" else None
            c.appeal_due_at=c.created_at+timedelta(hours=p.appeal_hours) if c.source_type=="DENIAL" else None
            c.escalation_due_at=c.created_at+timedelta(hours=p.escalation_hours)
            initialized+=1
        elif c.source_type=="DENIAL" and c.denial_response_due_at is None:
            c.denial_response_due_at=c.created_at+timedelta(hours=p.denial_response_hours)
            c.appeal_due_at=c.appeal_due_at or c.created_at+timedelta(hours=p.appeal_hours)
            c.escalation_due_at=c.escalation_due_at or c.created_at+timedelta(hours=p.escalation_hours)
            initialized+=1
        old=c.sla_status
        response_breached=c.source_type=="DENIAL" and c.first_response_at is None and c.denial_response_due_at is not None and now>=c.denial_response_due_at
        response_at_risk=c.source_type=="DENIAL" and c.first_response_at is None and c.denial_response_due_at is not None and now+timedelta(hours=24)>=c.denial_response_due_at
        resolution_breached=c.sla_due_at is not None and now>=c.sla_due_at
        escalation_due=c.escalation_due_at is not None and now>=c.escalation_due_at and c.first_response_at is None
        if resolution_breached or response_breached:state="BREACHED"
        elif response_at_risk or (c.sla_due_at is not None and now+timedelta(hours=24)>=c.sla_due_at):state="AT_RISK"
        else:state="ON_TRACK"
        c.sla_status=state
        if response_breached and old!="BREACHED":
            response_breaches+=1
            db.add(RevenueResolutionSLAEvent(case_id=c.id,event_type="FIRST_RESPONSE_BREACHED",from_level=c.escalation_level,to_level=min(3,c.escalation_level+1),note="Payer denial response deadline breached",actor_id=actor_id))
        if state=="BREACHED" and old!="BREACHED":
            c.sla_breached_at=c.sla_breached_at or now;c.escalation_level=min(3,c.escalation_level+1);c.status="ESCALATED";breached+=1
            db.add(RevenueResolutionSLAEvent(case_id=c.id,event_type="SLA_BREACHED",from_level=max(0,c.escalation_level-1),to_level=c.escalation_level,note="Resolution SLA breached",actor_id=actor_id))
        elif state=="AT_RISK" and c.escalation_level==0:
            c.escalation_level=1;escalated+=1
            db.add(RevenueResolutionSLAEvent(case_id=c.id,event_type="SLA_AT_RISK",from_level=0,to_level=1,note="SLA deadline approaching",actor_id=actor_id))
        if escalation_due and c.escalation_level<2:
            old_level=c.escalation_level;c.escalation_level=2;escalated+=1
            db.add(RevenueResolutionSLAEvent(case_id=c.id,event_type="ESCALATION_WINDOW_REACHED",from_level=old_level,to_level=2,note="Payer escalation window reached without first response",actor_id=actor_id))
        if c.source_type=="DENIAL" and c.appeal_due_at is not None and now+timedelta(hours=24)>=c.appeal_due_at and now<c.appeal_due_at: appeal_risk+=1
    record_audit(db,"SYNC_REVENUE_SLA","REVENUE_RESOLUTION_SLA",str(facility_id),{"initialized":initialized,"breached":breached,"escalated":escalated,"response_breaches":response_breaches,"appeal_risk":appeal_risk},user_id=actor_id,facility_id=facility_id,commit=False);db.commit()
    return {"initialized":initialized,"breached":breached,"escalated":escalated,"response_breaches":response_breaches,"appeal_risk":appeal_risk}

def escalation_queue(db,facility_id):
    now=datetime.now(timezone.utc)
    rows=db.scalars(select(RevenueResolutionCase).where(RevenueResolutionCase.facility_id==facility_id,RevenueResolutionCase.status.in_({"OPEN","IN_REVIEW","WAITING_EXTERNAL","ESCALATED"})).order_by(RevenueResolutionCase.sla_due_at.asc().nullslast()).limit(200)).all()
    out=[]
    for x in rows:
        if x.sla_due_at is None:continue
        hours=round((x.sla_due_at-now).total_seconds()/3600,1)
        response_hours=round((x.denial_response_due_at-now).total_seconds()/3600,1) if x.denial_response_due_at and x.first_response_at is None else None
        appeal_hours=round((x.appeal_due_at-now).total_seconds()/3600,1) if x.appeal_due_at else None
        action="ESCALATE_PAYER" if x.sla_status=="BREACHED" or x.escalation_level>=2 else "CONTACT_PAYER" if x.sla_status=="AT_RISK" else "MONITOR"
        if x.source_type=="DENIAL" and x.first_response_at is None and response_hours is not None and response_hours<=24:action="CONTACT_PAYER"
        if x.source_type=="DENIAL" and appeal_hours is not None and appeal_hours<=24:action="PREPARE_APPEAL"
        out.append({"case_id":str(x.id),"case_number":x.case_number,"source_type":x.source_type,"title":x.title,"priority":x.priority,"status":x.status,"sla_status":x.sla_status,"escalation_level":x.escalation_level,"sla_due_at":x.sla_due_at.isoformat(),"denial_response_due_at":x.denial_response_due_at.isoformat() if x.denial_response_due_at else None,"first_response_at":x.first_response_at.isoformat() if x.first_response_at else None,"appeal_due_at":x.appeal_due_at.isoformat() if x.appeal_due_at else None,"escalation_due_at":x.escalation_due_at.isoformat() if x.escalation_due_at else None,"hours_to_sla":hours,"hours_to_response":response_hours,"hours_to_appeal":appeal_hours,"amount_at_risk":float(x.amount_at_risk or 0),"recommended_action":action})
    return {"actions":len(out),"items":out}

def sla_events(db,facility_id,case_id):
    case=db.get(RevenueResolutionCase,case_id)
    if case is None:raise ValueError("RESOLUTION_CASE_NOT_FOUND")
    if case.facility_id!=facility_id:raise ValueError("FACILITY_ACCESS_DENIED")
    return list(db.scalars(select(RevenueResolutionSLAEvent).where(RevenueResolutionSLAEvent.case_id==case_id).order_by(RevenueResolutionSLAEvent.created_at.asc())).all())

def sla_overview(db,facility_id):
    rows=db.execute(select(RevenueResolutionCase.sla_status,func.count(RevenueResolutionCase.id),func.coalesce(func.sum(RevenueResolutionCase.amount_at_risk),0)).where(RevenueResolutionCase.facility_id==facility_id,RevenueResolutionCase.status.notin_({"RESOLVED","CLOSED"})).group_by(RevenueResolutionCase.sla_status)).all()
    return {"by_status":{str(s):{"count":int(c),"amount_at_risk":float(a or 0)} for s,c,a in rows}}

def payer_sla_performance(db,facility_id,days=90):
    since=datetime.now(timezone.utc)-timedelta(days=days)
    rows=db.execute(select(ClearinghouseCase.payer_id,func.count(ClearinghouseCase.id),func.sum(case((ClearinghouseCase.status=="REJECTED",1),else_=0)),func.coalesce(func.sum(ClearinghouseCase.claim_amount),0),func.coalesce(func.sum(ClearinghouseCase.paid_amount),0)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.updated_at>=since).group_by(ClearinghouseCase.payer_id)).all()
    out=[]
    for pid,total,denials,billed,paid in rows:
        p=db.get(Payer,pid) if pid else None;total=int(total);denials=int(denials or 0);b=float(billed or 0);pa=float(paid or 0)
        out.append({"payer_id":str(pid) if pid else None,"payer_name":p.name if p else "Unassigned","claims":total,"denials":denials,"denial_rate":round(denials/total*100,2) if total else 0,"billed":b,"paid":pa,"collection_rate":round(pa/b*100,2) if b else 0})
    return {"window_days":days,"payers":out}
