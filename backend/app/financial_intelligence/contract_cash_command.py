from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.financial_intelligence.guardrail_models import ContractComplianceGuardrail
from app.financial_intelligence.work_queue import CollectionWorkItem
from app.settlement.recovery import RevenueRecoveryCase
from app.financial_intelligence.resolution_models import RevenueResolutionCase

def contract_cash_command(db:Session, facility_id, days:int=90):
    guard_open = int(db.scalar(select(func.count(ContractComplianceGuardrail.id)).where(
        ContractComplianceGuardrail.facility_id==facility_id,
        ContractComplianceGuardrail.status.notin_(["RESOLVED","DISMISSED"])
    )) or 0)
    guard_risk = float(db.scalar(select(func.coalesce(func.sum(ContractComplianceGuardrail.amount_at_risk),0)).where(
        ContractComplianceGuardrail.facility_id==facility_id,
        ContractComplianceGuardrail.status.notin_(["RESOLVED","DISMISSED"])
    )) or 0)
    work_open = int(db.scalar(select(func.count(CollectionWorkItem.id)).where(
        CollectionWorkItem.facility_id==facility_id,
        CollectionWorkItem.status!="DONE"
    )) or 0)
    work_amount = float(db.scalar(select(func.coalesce(func.sum(CollectionWorkItem.outstanding_amount),0)).where(
        CollectionWorkItem.facility_id==facility_id,
        CollectionWorkItem.status!="DONE"
    )) or 0)
    recovery_open = int(db.scalar(select(func.count(RevenueRecoveryCase.id)).where(
        RevenueRecoveryCase.facility_id==facility_id,
        RevenueRecoveryCase.status.notin_(["RECOVERED","CLOSED","WRITTEN_OFF"])
    )) or 0)
    recovery_amount = float(db.scalar(select(func.coalesce(func.sum(RevenueRecoveryCase.outstanding_amount),0)).where(
        RevenueRecoveryCase.facility_id==facility_id,
        RevenueRecoveryCase.status.notin_(["RECOVERED","CLOSED","WRITTEN_OFF"])
    )) or 0)
    resolution_open = int(db.scalar(select(func.count(RevenueResolutionCase.id)).where(
        RevenueResolutionCase.facility_id==facility_id,
        RevenueResolutionCase.status.notin_(["RESOLVED","CLOSED"])
    )) or 0)
    resolution_risk = float(db.scalar(select(func.coalesce(func.sum(RevenueResolutionCase.amount_at_risk),0)).where(
        RevenueResolutionCase.facility_id==facility_id,
        RevenueResolutionCase.status.notin_(["RESOLVED","CLOSED"])
    )) or 0)
    return {
        "window_days":days,
        "guardrails":{"open":guard_open,"amount_at_risk":guard_risk},
        "collection_work":{"open":work_open,"outstanding":work_amount},
        "recovery":{"open":recovery_open,"outstanding":recovery_amount},
        "resolution":{"open":resolution_open,"amount_at_risk":resolution_risk},
        "total_exposure":guard_risk+recovery_amount+resolution_risk,
        "operational_queue":guard_open+work_open+recovery_open+resolution_open,
    }
