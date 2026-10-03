from datetime import datetime,timedelta,timezone
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.claim_clearinghouse.models import ClearinghouseCase
from app.financial_intelligence.guardrail_models import ContractComplianceGuardrail
from app.financial_intelligence.resolution_models import RevenueResolutionCase
from app.settlement.recovery import RevenueRecoveryCase
from app.financial_intelligence.work_queue import CollectionWorkItem

def executive_revenue_command(db:Session,facility_id,days:int=90):
    since=datetime.now(timezone.utc)-timedelta(days=days)
    billed=float(db.scalar(select(func.coalesce(func.sum(ClearinghouseCase.claim_amount),0)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.updated_at>=since)) or 0)
    paid=float(db.scalar(select(func.coalesce(func.sum(ClearinghouseCase.paid_amount),0)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.updated_at>=since)) or 0)
    claims=int(db.scalar(select(func.count(ClearinghouseCase.id)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.updated_at>=since)) or 0)
    guardrails=int(db.scalar(select(func.count(ContractComplianceGuardrail.id)).where(ContractComplianceGuardrail.facility_id==facility_id,ContractComplianceGuardrail.status.notin_(["RESOLVED","DISMISSED"]))) or 0)
    guardrail_risk=float(db.scalar(select(func.coalesce(func.sum(ContractComplianceGuardrail.amount_at_risk),0)).where(ContractComplianceGuardrail.facility_id==facility_id,ContractComplianceGuardrail.status.notin_(["RESOLVED","DISMISSED"]))) or 0)
    recovery=float(db.scalar(select(func.coalesce(func.sum(RevenueRecoveryCase.outstanding_amount),0)).where(RevenueRecoveryCase.facility_id==facility_id,RevenueRecoveryCase.status.notin_(["RECOVERED","CLOSED","WRITTEN_OFF"]))) or 0)
    resolution=float(db.scalar(select(func.coalesce(func.sum(RevenueResolutionCase.amount_at_risk),0)).where(RevenueResolutionCase.facility_id==facility_id,RevenueResolutionCase.status.notin_(["RESOLVED","CLOSED"]))) or 0)
    work_open=int(db.scalar(select(func.count(CollectionWorkItem.id)).where(CollectionWorkItem.facility_id==facility_id,CollectionWorkItem.status.notin_(["DONE"]))) or 0)
    work_amount=float(db.scalar(select(func.coalesce(func.sum(CollectionWorkItem.outstanding_amount),0)).where(CollectionWorkItem.facility_id==facility_id,CollectionWorkItem.status.notin_(["DONE"]))) or 0)
    gap=max(0,billed-paid)
    collection_rate=round(paid/billed*100,2) if billed else 0
    exposure=guardrail_risk+recovery+resolution
    actions=[]
    if guardrail_risk>0: actions.append({"action":"CONTRACT_COMPLIANCE_REVIEW","priority":"HIGH","amount":guardrail_risk})
    if recovery>0: actions.append({"action":"RECOVERY_FOLLOW_UP","priority":"HIGH","amount":recovery})
    if resolution>0: actions.append({"action":"RESOLUTION_ESCALATION","priority":"HIGH","amount":resolution})
    if gap>0: actions.append({"action":"PAYMENT_GAP_REVIEW","priority":"MEDIUM","amount":gap})
    return {"window_days":days,"claims":{"count":claims,"billed":billed,"paid":paid,"payment_gap":gap,"collection_rate":collection_rate},"guardrails":{"open":guardrails,"amount_at_risk":guardrail_risk},"recovery":{"outstanding":recovery},"resolution":{"amount_at_risk":resolution},"collection_work":{"open":work_open,"outstanding":work_amount},"combined_exposure":exposure,"actions":actions,"note":"Combined exposure is an operational signal and may overlap across linked workflows."}
