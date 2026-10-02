from datetime import datetime,timedelta,timezone
from uuid import UUID
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.provider_network.models import ProviderNetworkContract,ProviderNetworkMembership
from app.coverage.models import Payer
from app.claim_clearinghouse.models import ClearinghouseCase
from app.financial_intelligence.resolution_models import RevenueResolutionCase
from app.settlement.recovery import RevenueRecoveryCase
from app.financial_intelligence.sla_models import PayerSLAPolicy

def contract_renewal_intelligence(db:Session,facility_id:UUID,days:int=180):
    now=datetime.now(timezone.utc); horizon=now+timedelta(days=days)
    contracts=list(db.scalars(select(ProviderNetworkContract).where(ProviderNetworkContract.facility_id==facility_id).order_by(ProviderNetworkContract.renewal_due_at)).all())
    out=[]; actions=[]
    for c in contracts:
        payer=db.scalar(select(Payer).where(Payer.code==c.network_code))
        membership=db.scalar(select(ProviderNetworkMembership).where(ProviderNetworkMembership.facility_id==facility_id,ProviderNetworkMembership.network_code==c.network_code))
        since=now-timedelta(days=180)
        billed=float(db.scalar(select(func.coalesce(func.sum(ClearinghouseCase.claim_amount),0)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.payer_id==payer.id,ClearinghouseCase.updated_at>=since)) or 0) if payer else 0
        paid=float(db.scalar(select(func.coalesce(func.sum(ClearinghouseCase.paid_amount),0)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.payer_id==payer.id,ClearinghouseCase.updated_at>=since)) or 0) if payer else 0
        denials=int(db.scalar(select(func.count(ClearinghouseCase.id)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.payer_id==payer.id,ClearinghouseCase.status=="REJECTED",ClearinghouseCase.updated_at>=since)) or 0) if payer else 0
        claims=int(db.scalar(select(func.count(ClearinghouseCase.id)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.payer_id==payer.id,ClearinghouseCase.updated_at>=since)) or 0) if payer else 0
        recovery=float(db.scalar(select(func.coalesce(func.sum(RevenueRecoveryCase.outstanding_amount),0)).where(RevenueRecoveryCase.facility_id==facility_id,RevenueRecoveryCase.payer_id==payer.id,RevenueRecoveryCase.status.notin_({"RECOVERED","CLOSED","WRITTEN_OFF"}))) or 0) if payer else 0
        risk=[]
        if c.renewal_due_at and c.renewal_due_at<=horizon:risk.append("RENEWAL_DUE")
        if claims and denials/claims>=0.15:risk.append("HIGH_DENIAL_RATE")
        if billed and paid/billed<0.80:risk.append("LOW_COLLECTION_RATE")
        if recovery>0:risk.append("RECOVERY_EXPOSURE")
        if c.payment_terms_days>45:risk.append("LONG_PAYMENT_TERMS")
        if not membership or membership.participation_status!="ACTIVE":risk.append("EMPANELMENT_GAP")
        if risk: actions.append({"contract_id":str(c.id),"payer_name":payer.name if payer else c.network_code,"priority":"HIGH" if len(risk)>=2 else "MEDIUM","action":"RENEWAL_REVIEW","reason":"; ".join(risk)})
        out.append({"contract_id":str(c.id),"contract_reference":c.contract_reference,"network_code":c.network_code,"payer_name":payer.name if payer else c.network_code,"status":c.status,"renewal_due_at":c.renewal_due_at.isoformat() if c.renewal_due_at else None,"payment_terms_days":c.payment_terms_days,"billed_180d":billed,"paid_180d":paid,"collection_rate_180d":round(paid/billed*100,2) if billed else 0,"claims_180d":claims,"denials_180d":denials,"denial_rate_180d":round(denials/claims*100,2) if claims else 0,"recovery_outstanding":recovery,"risk_signals":risk})
    return {"horizon_days":days,"contracts":out,"actions":actions}
