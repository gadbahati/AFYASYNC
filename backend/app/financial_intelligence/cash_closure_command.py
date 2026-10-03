from decimal import Decimal
from uuid import UUID
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.financial_intelligence.work_queue import CollectionWorkItem
from app.financial_intelligence.guardrail_models import ContractComplianceGuardrail
from app.financial_intelligence.resolution_models import RevenueResolutionCase
from app.settlement.recovery import RevenueRecoveryCase

def _m(v): return Decimal(str(v or 0))

def cash_closure_command(db:Session,facility_id:UUID,limit:int=100):
    work=list(db.scalars(select(CollectionWorkItem).where(
        CollectionWorkItem.facility_id==facility_id,
        CollectionWorkItem.status.in_({"OPEN","IN_PROGRESS","SNOOZED"})
    ).order_by(CollectionWorkItem.priority.desc(),CollectionWorkItem.created_at.asc()).limit(max(1,min(limit,200)))).all())

    open_work=len(work)
    work_exposure=sum((_m(x.outstanding_amount) for x in work),Decimal("0"))

    guardrails=list(db.scalars(select(ContractComplianceGuardrail).where(
        ContractComplianceGuardrail.facility_id==facility_id,
        ContractComplianceGuardrail.status.in_({"OPEN","IN_REVIEW"})
    )).all())
    recoveries=list(db.scalars(select(RevenueRecoveryCase).where(
        RevenueRecoveryCase.facility_id==facility_id,
        RevenueRecoveryCase.status.in_({"OPEN","IN_PROGRESS","DISPUTED"})
    )).all())
    resolutions=list(db.scalars(select(RevenueResolutionCase).where(
        RevenueResolutionCase.facility_id==facility_id,
        RevenueResolutionCase.status.notin_({"RESOLVED","CLOSED"})
    )).all())

    guardrail_risk=sum((_m(x.amount_at_risk) for x in guardrails),Decimal("0"))
    recovery_outstanding=sum((_m(x.outstanding_amount) for x in recoveries),Decimal("0"))
    resolution_risk=sum((_m(x.amount_at_risk) for x in resolutions),Decimal("0"))

    terminal_guardrails=db.scalar(select(func.count()).select_from(ContractComplianceGuardrail).where(
        ContractComplianceGuardrail.facility_id==facility_id,
        ContractComplianceGuardrail.status.in_({"RESOLVED","DISMISSED"})
    )) or 0
    terminal_recoveries=db.scalar(select(func.count()).select_from(RevenueRecoveryCase).where(
        RevenueRecoveryCase.facility_id==facility_id,
        RevenueRecoveryCase.status.in_({"RECOVERED","CLOSED","WRITTEN_OFF"})
    )) or 0
    terminal_resolutions=db.scalar(select(func.count()).select_from(RevenueResolutionCase).where(
        RevenueResolutionCase.facility_id==facility_id,
        RevenueResolutionCase.status.in_({"RESOLVED","CLOSED"})
    )) or 0

    exceptions=sum(1 for x in guardrails if x.status=="DISMISSED")+sum(1 for x in recoveries if x.status=="WRITTEN_OFF")
    exposure=guardrail_risk+recovery_outstanding+resolution_risk

    return {
        "open_work":open_work,
        "work_exposure":float(work_exposure),
        "open_guardrails":len(guardrails),
        "guardrail_exposure":float(guardrail_risk),
        "open_recoveries":len(recoveries),
        "recovery_outstanding":float(recovery_outstanding),
        "open_resolutions":len(resolutions),
        "resolution_exposure":float(resolution_risk),
        "combined_operational_exposure":float(exposure),
        "terminal_guardrails":terminal_guardrails,
        "terminal_recoveries":terminal_recoveries,
        "terminal_resolutions":terminal_resolutions,
        "exceptions":exceptions,
        "status":"ATTENTION" if exposure>0 or open_work>0 else "CLEAR",
        "note":"Combined operational exposure can overlap across guardrails, recovery, resolution, and work items. It is not an accounting loss or a cash-recovery total."
    }
