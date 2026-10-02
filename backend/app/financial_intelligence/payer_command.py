from datetime import datetime,timedelta,timezone
from sqlalchemy import select,func,case
from sqlalchemy.orm import Session
from app.coverage.models import Payer
from app.claim_clearinghouse.models import ClearinghouseCase
from app.settlement.recovery import RevenueRecoveryCase
from app.financial_intelligence.resolution_models import RevenueResolutionCase
from app.financial_intelligence.sla_models import PayerSLAPolicy
from app.provider_network.models import ProviderNetworkMembership,ProviderNetworkContract
def payer_command(db:Session,facility_id,days=90):
    since=datetime.now(timezone.utc)-timedelta(days=days)
    payers=list(db.scalars(select(Payer).order_by(Payer.name)).all())
    out=[]
    for p in payers:
        claims=db.execute(select(func.count(ClearinghouseCase.id),func.coalesce(func.sum(ClearinghouseCase.claim_amount),0),func.coalesce(func.sum(ClearinghouseCase.paid_amount),0),func.sum(case((ClearinghouseCase.status=="REJECTED",1),else_=0))).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.payer_id==p.id,ClearinghouseCase.updated_at>=since)).one()
        total,billed,paid,denials=claims;total=int(total or 0);billed=float(billed or 0);paid=float(paid or 0);denials=int(denials or 0)
        recovery=db.execute(select(func.coalesce(func.sum(RevenueRecoveryCase.outstanding_amount),0)).where(RevenueRecoveryCase.facility_id==facility_id,RevenueRecoveryCase.payer_id==p.id,RevenueRecoveryCase.status.notin_({"RECOVERED","CLOSED","WRITTEN_OFF"}))).scalar() or 0
        resolution=db.execute(select(func.count(RevenueResolutionCase.id),func.coalesce(func.sum(RevenueResolutionCase.amount_at_risk),0)).where(RevenueResolutionCase.facility_id==facility_id,RevenueResolutionCase.payer_id==p.id,RevenueResolutionCase.status.notin_({"RESOLVED","CLOSED"}))).one()
        active_cases,at_risk=resolution
        sla=db.scalar(select(PayerSLAPolicy).where(PayerSLAPolicy.facility_id==facility_id,PayerSLAPolicy.payer_id==p.id,PayerSLAPolicy.active.is_(True)))
        membership=db.scalar(select(ProviderNetworkMembership).where(ProviderNetworkMembership.facility_id==facility_id,ProviderNetworkMembership.network_code==p.code))
        contract=db.scalar(select(ProviderNetworkContract).where(ProviderNetworkContract.facility_id==facility_id,ProviderNetworkContract.network_code==p.code).order_by(ProviderNetworkContract.created_at.desc()))
        out.append({"payer_id":str(p.id),"payer_name":p.name,"payer_code":p.code,"claims":total,"billed":billed,"paid":paid,"outstanding":max(0,billed-paid),"denials":denials,"denial_rate":round(denials/total*100,2) if total else 0,"collection_rate":round(paid/billed*100,2) if billed else 0,"recovery_outstanding":float(recovery),"active_resolution_cases":int(active_cases or 0),"resolution_amount_at_risk":float(at_risk or 0),"sla_configured":bool(sla),"denial_response_hours":sla.denial_response_hours if sla else None,"resolution_hours":sla.resolution_hours if sla else None,"appeal_hours":sla.appeal_hours if sla else None,"contract_status":contract.status if contract else None,"payment_terms_days":contract.payment_terms_days if contract else None,"empanelment_status":membership.participation_status if membership else None,"claims_enabled":membership.claims_enabled if membership else None})
    out.sort(key=lambda x:(-x["resolution_amount_at_risk"],-x["outstanding"],-x["denials"]))
    return {"window_days":days,"payers":out}
def payer_optimization(db,facility_id,days=90):
    rows=payer_command(db,facility_id,days)["payers"]
    actions=[]
    for p in rows:
        if p["claims"]==0 and not p["contract_status"] and not p["empanelment_status"]:
            continue
        if p["sla_configured"] is False and p["claims"]>0:
            actions.append({"payer_id":p["payer_id"],"payer_name":p["payer_name"],"action":"CONFIGURE_SLA","reason":"Claims are active but no payer-specific SLA policy is configured.","priority":"HIGH"})
        if p["denial_rate"]>=15 and p["claims"]>=5:
            actions.append({"payer_id":p["payer_id"],"payer_name":p["payer_name"],"action":"DENIAL_REVIEW","reason":f"Denial rate is {p['denial_rate']}% over the selected window.","priority":"HIGH"})
        if p["collection_rate"]<80 and p["billed"]>0:
            actions.append({"payer_id":p["payer_id"],"payer_name":p["payer_name"],"action":"REIMBURSEMENT_REVIEW","reason":f"Collection rate is {p['collection_rate']}%. Review payment terms, tariffs and unresolved claims.","priority":"HIGH"})
        if p["recovery_outstanding"]>0:
            actions.append({"payer_id":p["payer_id"],"payer_name":p["payer_name"],"action":"RECOVERY_FOLLOW_UP","reason":f"Outstanding recovery exposure is KES {p['recovery_outstanding']:,.0f}.","priority":"MEDIUM"})
        if p["contract_status"]=="ACTIVE" and p["payment_terms_days"] and p["payment_terms_days"]>45:
            actions.append({"payer_id":p["payer_id"],"payer_name":p["payer_name"],"action":"PAYMENT_TERMS_REVIEW","reason":f"Contract payment terms are {p['payment_terms_days']} days.","priority":"MEDIUM"})
        if p["claims_enabled"] is False and p["claims"]>0:
            actions.append({"payer_id":p["payer_id"],"payer_name":p["payer_name"],"action":"ENABLE_CLAIMS_WORKFLOW","reason":"Claims activity exists while the provider-network membership has claims disabled.","priority":"HIGH"})
    order={"HIGH":0,"MEDIUM":1,"LOW":2};actions.sort(key=lambda x:order[x["priority"]])
    return {"window_days":days,"actions":actions}

def payer_summary(db,facility_id,days=90):
    rows=payer_command(db,facility_id,days)["payers"]
    return {"window_days":days,"payer_count":len(rows),"configured_sla":sum(x["sla_configured"] for x in rows),"active_contracts":sum(x["contract_status"]=="ACTIVE" for x in rows),"open_resolution_cases":sum(x["active_resolution_cases"] for x in rows),"outstanding":sum(x["outstanding"] for x in rows),"recovery_outstanding":sum(x["recovery_outstanding"] for x in rows),"denial_exposure":sum(x["resolution_amount_at_risk"] for x in rows)}

# Phase 66: payer command intelligence is deployment-tracked with the backend service.
