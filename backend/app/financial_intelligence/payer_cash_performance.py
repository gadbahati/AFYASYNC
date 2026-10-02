from datetime import datetime,timedelta,timezone
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.coverage.models import Payer
from app.claim_clearinghouse.models import ClearinghouseCase
from app.settlement.recovery import RevenueRecoveryCase
from app.financial_intelligence.resolution_models import RevenueResolutionCase
from app.financial_intelligence.guardrail_models import ContractComplianceGuardrail
from app.provider_network.models import ProviderNetworkContract

def payer_contract_cash_performance(db:Session,facility_id,days:int=90):
    since=datetime.now(timezone.utc)-timedelta(days=days)
    payers=list(db.scalars(select(Payer).order_by(Payer.name)).all())
    rows=[]
    for p in payers:
        claims,billed,paid=db.execute(select(func.count(ClearinghouseCase.id),func.coalesce(func.sum(ClearinghouseCase.claim_amount),0),func.coalesce(func.sum(ClearinghouseCase.paid_amount),0)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.payer_id==p.id,ClearinghouseCase.updated_at>=since)).one()
        denied=int(db.scalar(select(func.count(ClearinghouseCase.id)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.payer_id==p.id,ClearinghouseCase.status=="REJECTED",ClearinghouseCase.updated_at>=since)) or 0)
        recovery=float(db.scalar(select(func.coalesce(func.sum(RevenueRecoveryCase.outstanding_amount),0)).where(RevenueRecoveryCase.facility_id==facility_id,RevenueRecoveryCase.payer_id==p.id,RevenueRecoveryCase.status.notin_(["RECOVERED","CLOSED","WRITTEN_OFF"]))) or 0)
        resolution=float(db.scalar(select(func.coalesce(func.sum(RevenueResolutionCase.amount_at_risk),0)).where(RevenueResolutionCase.facility_id==facility_id,RevenueResolutionCase.payer_id==p.id,RevenueResolutionCase.status.notin_(["RESOLVED","CLOSED"]))) or 0)
        guard=float(db.scalar(select(func.coalesce(func.sum(ContractComplianceGuardrail.amount_at_risk),0)).where(ContractComplianceGuardrail.facility_id==facility_id,ContractComplianceGuardrail.payer_id==p.id,ContractComplianceGuardrail.status.notin_(["RESOLVED","DISMISSED"]))) or 0)
        contract=db.scalar(select(ProviderNetworkContract).where(ProviderNetworkContract.facility_id==facility_id,ProviderNetworkContract.network_code==p.code).order_by(ProviderNetworkContract.created_at.desc()))
        billed=float(billed or 0);paid=float(paid or 0);claims=int(claims or 0)
        payment_gap=max(0,billed-paid)
        exposure=recovery+resolution+guard
        leakage_rate=round(exposure/billed*100,2) if billed else 0
        recovery_yield=round((1-(recovery/billed))*100,2) if billed and recovery else (100 if billed else 0)
        rows.append({"payer_id":str(p.id),"payer_name":p.name,"payer_code":p.code,"claims":claims,"billed":billed,"paid":paid,"payment_gap":payment_gap,"collection_rate":round(paid/billed*100,2) if billed else 0,"denials":denied,"denial_rate":round(denied/claims*100,2) if claims else 0,"guardrail_exposure":guard,"recovery_outstanding":recovery,"resolution_exposure":resolution,"total_exposure":exposure,"exposure_rate":leakage_rate,"recovery_yield":recovery_yield,"contract_status":contract.status if contract else None})
    rows=[x for x in rows if x["claims"] or x["total_exposure"]]
    rows.sort(key=lambda x:(-x["total_exposure"],-x["payment_gap"]))
    totals={"billed":sum(x["billed"] for x in rows),"paid":sum(x["paid"] for x in rows),"payment_gap":sum(x["payment_gap"] for x in rows),"exposure":sum(x["total_exposure"] for x in rows),"guardrails":sum(x["guardrail_exposure"] for x in rows),"recovery":sum(x["recovery_outstanding"] for x in rows),"resolution":sum(x["resolution_exposure"] for x in rows)}
    return {"window_days":days,"payers":rows,"totals":totals}
