from datetime import datetime,timedelta,timezone
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.coverage.models import Payer
from app.claim_clearinghouse.models import ClearinghouseCase
from app.settlement.recovery import RevenueRecoveryCase
from app.financial_intelligence.resolution_models import RevenueResolutionCase
from app.financial_intelligence.guardrail_models import ContractComplianceGuardrail

def revenue_leakage_intelligence(db:Session,facility_id,days:int=90):
    since=datetime.now(timezone.utc)-timedelta(days=days)
    payers=list(db.scalars(select(Payer).order_by(Payer.name)).all())
    rows=[]
    for p in payers:
        billed=float(db.scalar(select(func.coalesce(func.sum(ClearinghouseCase.claim_amount),0)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.payer_id==p.id,ClearinghouseCase.updated_at>=since)) or 0)
        paid=float(db.scalar(select(func.coalesce(func.sum(ClearinghouseCase.paid_amount),0)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.payer_id==p.id,ClearinghouseCase.updated_at>=since)) or 0)
        denials=float(db.scalar(select(func.coalesce(func.sum(ClearinghouseCase.claim_amount),0)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.payer_id==p.id,ClearinghouseCase.status=="REJECTED",ClearinghouseCase.updated_at>=since)) or 0)
        recovery=float(db.scalar(select(func.coalesce(func.sum(RevenueRecoveryCase.outstanding_amount),0)).where(RevenueRecoveryCase.facility_id==facility_id,RevenueRecoveryCase.payer_id==p.id,RevenueRecoveryCase.status.notin_(["RECOVERED","CLOSED","WRITTEN_OFF"]))) or 0)
        resolution=float(db.scalar(select(func.coalesce(func.sum(RevenueResolutionCase.amount_at_risk),0)).where(RevenueResolutionCase.facility_id==facility_id,RevenueResolutionCase.payer_id==p.id,RevenueResolutionCase.status.notin_(["RESOLVED","CLOSED"]))) or 0)
        guard=float(db.scalar(select(func.coalesce(func.sum(ContractComplianceGuardrail.amount_at_risk),0)).where(ContractComplianceGuardrail.facility_id==facility_id,ContractComplianceGuardrail.payer_id==p.id,ContractComplianceGuardrail.status.notin_(["RESOLVED","DISMISSED"]))) or 0)
        payment_gap=max(0,billed-paid)
        attributable=denials+guard
        operational=guard+recovery+resolution
        recovered_proxy=max(0,attributable-recovery)
        yield_pct=round(recovered_proxy/attributable*100,2) if attributable else 0
        rows.append({"payer_id":str(p.id),"payer_name":p.name,"billed":billed,"paid":paid,"payment_gap":payment_gap,"denial_value":denials,"guardrail_exposure":guard,"recovery_outstanding":recovery,"resolution_exposure":resolution,"attributable_exposure":attributable,"operational_exposure":operational,"recovery_yield_proxy":yield_pct})
    rows=[x for x in rows if x["billed"] or x["operational_exposure"]]
    rows.sort(key=lambda x:(-x["attributable_exposure"],-x["payment_gap"]))
    totals={k:sum(x[k] for x in rows) for k in ["billed","paid","payment_gap","denial_value","guardrail_exposure","recovery_outstanding","resolution_exposure","attributable_exposure","operational_exposure"]}
    totals["recovery_yield_proxy"]=round(max(0,totals["attributable_exposure"]-totals["recovery_outstanding"])/totals["attributable_exposure"]*100,2) if totals["attributable_exposure"] else 0
    actions=[]
    for x in rows:
        if x["denial_value"]>0: actions.append({"payer_id":x["payer_id"],"payer_name":x["payer_name"],"action":"DENIAL_LEAKAGE_REVIEW","priority":"HIGH","amount":x["denial_value"]})
        if x["guardrail_exposure"]>0: actions.append({"payer_id":x["payer_id"],"payer_name":x["payer_name"],"action":"CONTRACT_VARIANCE_REVIEW","priority":"HIGH","amount":x["guardrail_exposure"]})
        if x["recovery_outstanding"]>0: actions.append({"payer_id":x["payer_id"],"payer_name":x["payer_name"],"action":"RECOVERY_YIELD_REVIEW","priority":"MEDIUM","amount":x["recovery_outstanding"]})
    return {"window_days":days,"payers":rows,"totals":totals,"actions":actions}
