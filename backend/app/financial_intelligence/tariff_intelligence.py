from datetime import datetime,timedelta,timezone
from uuid import UUID
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.claims.models import Claim,ClaimItem
from app.billing.models import Service
from app.coverage.models import Payer
from app.provider_network.models import ProviderNetworkService

def tariff_intelligence(db:Session,facility_id:UUID,days:int=90,limit:int=100):
    since=datetime.now(timezone.utc)-timedelta(days=days)
    rows=db.execute(
        select(ClaimItem.service_code,Service.name,Claim.payer_id,Payer.name,func.sum(ClaimItem.quantity),func.sum(ClaimItem.amount),func.sum(Claim.approved_amount),func.sum(Claim.paid_amount),func.count(func.distinct(Claim.id)))
        .join(Claim,Claim.id==ClaimItem.claim_id)
        .join(Service,Service.code==ClaimItem.service_code)
        .join(Payer,Payer.id==Claim.payer_id,isouter=True)
        .where(ClaimItem.claim_id==Claim.id,Service.facility_id==facility_id,Claim.updated_at>=since)
        .group_by(ClaimItem.service_code,Service.name,Claim.payer_id,Payer.name)
        .order_by(func.sum(ClaimItem.amount).desc()).limit(min(max(limit,1),500))
    ).all()
    out=[]
    for code,name,payer_id,payer_name,qty,billed,approved,paid,claims in rows:
        payer_code=db.scalar(select(Payer.code).where(Payer.id==payer_id)) if payer_id else None
        contract=db.scalar(select(ProviderNetworkService).where(ProviderNetworkService.facility_id==facility_id,ProviderNetworkService.network_code==payer_code,ProviderNetworkService.service_code==code,ProviderNetworkService.status=="ACTIVE"))
        contracted=float(contract.tariff_amount) if contract and contract.tariff_amount is not None else None
        billed=float(billed or 0); approved=float(approved or 0); paid=float(paid or 0); qty=float(qty or 0)
        billed_unit=billed/qty if qty else 0
        expected_contract=contracted*qty if contracted is not None else None
        variance=(expected_contract-billed) if expected_contract is not None else None
        payment_gap=max(0,approved-paid)
        out.append({"service_code":code,"service_name":name,"payer_id":str(payer_id) if payer_id else None,"payer_name":payer_name or "Unknown","claims":int(claims or 0),"quantity":qty,"billed":billed,"approved":approved,"paid":paid,"billed_unit":billed_unit,"contracted_unit":contracted,"contracted_value":expected_contract,"contract_variance":variance,"payment_gap":payment_gap,"approval_rate":round(approved/billed*100,2) if billed else 0,"collection_rate":round(paid/billed*100,2) if billed else 0,"contracted":contracted is not None})
    actions=[]
    for x in out:
        if x["contracted"] and x["contract_variance"] is not None and abs(x["contract_variance"])>=1000:
            actions.append({"priority":"HIGH","action":"TARIFF_VARIANCE_REVIEW","service_code":x["service_code"],"payer_name":x["payer_name"],"reason":f"Contracted tariff basis differs from billed value by KES {abs(x['contract_variance']):,.0f} over the selected window."})
        if x["claims"]>=3 and x["approval_rate"]<80:
            actions.append({"priority":"HIGH","action":"SERVICE_ADJUDICATION_REVIEW","service_code":x["service_code"],"payer_name":x["payer_name"],"reason":f"Approval rate is {x['approval_rate']}%."})
        if x["payment_gap"]>=1000:
            actions.append({"priority":"MEDIUM","action":"PAYMENT_GAP_REVIEW","service_code":x["service_code"],"payer_name":x["payer_name"],"reason":f"Approved-to-paid gap is KES {x['payment_gap']:,.0f}."})
        if not x["contracted"] and x["claims"]>=3:
            actions.append({"priority":"MEDIUM","action":"CONTRACT_TARIFF_CHECK","service_code":x["service_code"],"payer_name":x["payer_name"],"reason":"Claims activity exists but no active provider-network tariff was found for this service/payer combination."})
    return {"window_days":days,"services":out,"actions":actions}
