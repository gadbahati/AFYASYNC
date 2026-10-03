from datetime import datetime,timezone
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.financial_intelligence.work_queue import CollectionWorkItem
from app.financial_intelligence.guardrail_models import ContractComplianceGuardrail
from app.settlement.recovery import RevenueRecoveryCase
from app.financial_intelligence.resolution_models import RevenueResolutionCase

def revenue_action_priorities(db:Session,facility_id,limit:int=50):
    items=[]
    guards=list(db.scalars(select(ContractComplianceGuardrail).where(ContractComplianceGuardrail.facility_id==facility_id,ContractComplianceGuardrail.status.in_(["OPEN","IN_REVIEW"])).order_by(ContractComplianceGuardrail.created_at.asc()).limit(limit)).all())
    for x in guards:
        score={"CRITICAL":100,"HIGH":75,"MEDIUM":45,"LOW":20}.get(x.severity,20)
        items.append({"source":"GUARDRAIL","source_id":str(x.id),"title":x.title,"priority_score":score,"severity":x.severity,"amount":float(x.amount_at_risk or 0),"recommended_action":"REVIEW_CONTRACT_COMPLIANCE"})
    recs=list(db.scalars(select(RevenueRecoveryCase).where(RevenueRecoveryCase.facility_id==facility_id,RevenueRecoveryCase.status.in_(["OPEN","IN_PROGRESS","DISPUTED"])).order_by(RevenueRecoveryCase.created_at.asc()).limit(limit)).all())
    now=datetime.now(timezone.utc)
    for x in recs:
        age=(now-x.created_at).days if x.created_at else 0
        score=min(95,35+age)
        if float(x.outstanding_amount or 0)>=100000: score+=10
        items.append({"source":"RECOVERY","source_id":str(x.id),"title":x.reason or x.case_number,"priority_score":min(score,100),"severity":"HIGH" if score>=75 else "MEDIUM","amount":float(x.outstanding_amount or 0),"recommended_action":"FOLLOW_UP_RECOVERY"})
    resolutions=list(db.scalars(select(RevenueResolutionCase).where(RevenueResolutionCase.facility_id==facility_id,RevenueResolutionCase.status.notin_(["RESOLVED","CLOSED"])).order_by(RevenueResolutionCase.created_at.asc()).limit(limit)).all())
    for x in resolutions:
        amount=float(x.amount_at_risk or 0);score=65+(20 if amount>=100000 else 0)
        items.append({"source":"RESOLUTION","source_id":str(x.id),"title":x.title,"priority_score":score,"severity":"HIGH" if score>=75 else "MEDIUM","amount":amount,"recommended_action":"ESCALATE_RESOLUTION"})
    items.sort(key=lambda x:(-x["priority_score"],-x["amount"]))
    return {"items":items[:limit],"count":min(len(items),limit)}
