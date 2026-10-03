from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.financial_intelligence.work_queue import CollectionWorkItem
from app.financial_intelligence.guardrail_models import ContractComplianceGuardrail
from app.financial_intelligence.resolution_models import RevenueResolutionCase
from app.settlement.recovery import RevenueRecoveryCase

ACTIVE_STATUSES={"OPEN","IN_PROGRESS","SNOOZED"}

def _money(value):
    return Decimal(str(value or 0))

def verify_cash_closure(db:Session,facility_id:UUID,actor_id:UUID,limit:int=200):
    items=list(db.scalars(select(CollectionWorkItem).where(
        CollectionWorkItem.facility_id==facility_id,
        CollectionWorkItem.status.in_(ACTIVE_STATUSES)
    ).order_by(CollectionWorkItem.created_at.asc()).limit(max(1,min(limit,500)))).all())

    verified=[]
    exceptions=[]
    pending=[]
    for item in items:
        source=None
        state="PENDING"
        reason="Unsupported source type for cash closure verification."
        if item.source_type in {"CONTRACT_GUARDRAIL","REVENUE_ACTION_GUARDRAIL"}:
            source=db.get(ContractComplianceGuardrail,item.source_id)
            if source is None:
                state="PENDING"; reason="Source guardrail record not found."
            elif source.status=="DISMISSED":
                state="EXCEPTION"; reason="Guardrail dismissed; closure is operationally closed but not cash recovery."
            elif source.status=="RESOLVED" and _money(source.amount_at_risk)<=0:
                state="VERIFIED"; reason="Guardrail resolved with no remaining amount at risk."
            else:
                reason=f"Guardrail status={source.status}; amount_at_risk={source.amount_at_risk}."
        elif item.source_type=="REVENUE_ACTION_RECOVERY":
            source=db.get(RevenueRecoveryCase,item.source_id)
            if source is None:
                reason="Source recovery record not found."
            elif source.status in {"RECOVERED","CLOSED"} and _money(source.outstanding_amount)<=0:
                state="VERIFIED"; reason="Recovery is terminal with zero outstanding balance."
            elif source.status=="WRITTEN_OFF":
                state="EXCEPTION"; reason="Recovery was written off; no cash recovery is verified."
            else:
                reason=f"Recovery status={source.status}; outstanding={source.outstanding_amount}."
        elif item.source_type=="REVENUE_ACTION_RESOLUTION":
            source=db.get(RevenueResolutionCase,item.source_id)
            if source is None:
                reason="Source resolution record not found."
            elif source.status in {"RESOLVED","CLOSED"} and _money(source.amount_at_risk)<=0:
                state="VERIFIED"; reason="Resolution is terminal with zero amount at risk."
            else:
                reason=f"Resolution status={source.status}; amount_at_risk={source.amount_at_risk}."
        else:
            pending.append({"work_id":str(item.id),"source_type":item.source_type,"state":"PENDING","reason":reason})
            continue

        row={"work_id":str(item.id),"source_type":item.source_type,"source_id":str(item.source_id),"state":state,"reason":reason}
        if state=="VERIFIED":
            verified.append(row)
        elif state=="EXCEPTION":
            exceptions.append(row)
        else:
            pending.append(row)

    record_audit(db,actor_id,"VERIFY_REVENUE_CASH_CLOSURE","collection_work_items",str(facility_id),{
        "checked":len(items),"verified":len(verified),"exceptions":len(exceptions),"pending":len(pending)
    })
    db.commit()
    return {
        "checked":len(items),
        "verified":len(verified),
        "exceptions":len(exceptions),
        "pending":len(pending),
        "verified_items":verified,
        "exceptions_items":exceptions,
        "pending_items":pending,
        "note":"Cash closure is verified only when the underlying source is terminal and its remaining financial exposure is zero. Written-off and dismissed items are reported as exceptions, not recovered cash."
    }
