from datetime import datetime,timedelta,timezone
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.claim_clearinghouse.models import ClearinghouseCase
from app.financial_intelligence.guardrail_models import ContractComplianceGuardrail
from app.settlement.recovery import RevenueRecoveryCase
from app.financial_intelligence.resolution_models import RevenueResolutionCase
from app.collection_work.work_queue import CollectionWorkItem

def revenue_control_tower(db:Session,facility_id,days:int=30):
    since=datetime.now(timezone.utc)-timedelta(days=days)
    rejected=int(db.scalar(select(func.count(ClearinghouseCase.id)).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.status=="REJECTED",ClearinghouseCase.updated_at>=since)) or 0)
    open_guard=int(db.scalar(select(func.count(ContractComplianceGuardrail.id)).where(ContractComplianceGuardrail.facility_id==facility_id,ContractComplianceGuardrail.status.notin_(["RESOLVED","DISMISSED"]))) or 0)
    open_recovery=int(db.scalar(select(func.count(RevenueRecoveryCase.id)).where(RevenueRecoveryCase.facility_id==facility_id,RevenueRecoveryCase.status.in_(["OPEN","IN_PROGRESS","DISPUTED"]))) or 0)
    open_resolution=int(db.scalar(select(func.count(RevenueResolutionCase.id)).where(RevenueResolutionCase.facility_id==facility_id,RevenueResolutionCase.status.notin_(["RESOLVED","CLOSED"]))) or 0)
    work=int(db.scalar(select(func.count(CollectionWorkItem.id)).where(CollectionWorkItem.facility_id==facility_id,CollectionWorkItem.status.notin_(["DONE"]))) or 0)
    critical=int(db.scalar(select(func.count(ContractComplianceGuardrail.id)).where(ContractComplianceGuardrail.facility_id==facility_id,ContractComplianceGuardrail.status.notin_(["RESOLVED","DISMISSED"]),ContractComplianceGuardrail.severity=="CRITICAL")) or 0)
    alerts=[]
    if critical: alerts.append({"severity":"CRITICAL","signal":"CRITICAL_CONTRACT_GUARDRAILS","count":critical})
    if rejected: alerts.append({"severity":"HIGH","signal":"RECENT_CLAIM_REJECTIONS","count":rejected})
    if open_recovery: alerts.append({"severity":"HIGH","signal":"OPEN_RECOVERY_CASES","count":open_recovery})
    if open_resolution: alerts.append({"severity":"MEDIUM","signal":"OPEN_RESOLUTION_CASES","count":open_resolution})
    return {"window_days":days,"signals":{"claim_rejections":rejected,"guardrails":open_guard,"recovery":open_recovery,"resolution":open_resolution,"collection_work":work},"alerts":alerts,"control_status":"ATTENTION" if alerts else "STABLE"}
