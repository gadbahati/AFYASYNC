from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.financial_intelligence.guardrail_models import ContractComplianceGuardrail
from app.financial_intelligence.work_queue import CollectionWorkItem
from app.settlement.models import SettlementReconciliation, SettlementBatch
from app.settlement.recovery import RevenueRecoveryCase, open_recovery

def sync_guardrail_work(db:Session, facility_id:UUID, actor_id:UUID, limit:int=200):
    rows=db.scalars(select(ContractComplianceGuardrail).where(
        ContractComplianceGuardrail.facility_id==facility_id,
        ContractComplianceGuardrail.status.in_(["OPEN","IN_REVIEW"])
    ).order_by(ContractComplianceGuardrail.severity.desc(),ContractComplianceGuardrail.created_at.asc()).limit(max(1,min(limit,500)))).all()
    created=0
    for g in rows:
        existing=db.scalar(select(CollectionWorkItem).where(
            CollectionWorkItem.facility_id==facility_id,
            CollectionWorkItem.source_type=="CONTRACT_GUARDRAIL",
            CollectionWorkItem.source_id==g.id,
            CollectionWorkItem.status!="DONE"
        ))
        priority=g.severity if g.severity in {"LOW","MEDIUM","HIGH","CRITICAL"} else "MEDIUM"
        if existing:
            existing.priority=priority
            existing.outstanding_amount=g.amount_at_risk
            existing.title=g.title
            existing.note=g.detail
            continue
        days=1 if priority=="CRITICAL" else 2 if priority=="HIGH" else 5 if priority=="MEDIUM" else 10
        db.add(CollectionWorkItem(
            facility_id=facility_id,source_type="CONTRACT_GUARDRAIL",source_id=g.id,
            title=g.title,priority=priority,status="OPEN",
            due_at=datetime.now(timezone.utc)+timedelta(days=days),
            outstanding_amount=g.amount_at_risk,note=g.detail
        ))
        created+=1
    db.flush()
    record_audit(db,actor_id,"SYNC_CONTRACT_GUARDRAIL_WORK","collection_work_items",str(facility_id),{"created":created,"candidates":len(rows)})
    db.commit()
    return {"created":created,"candidates":len(rows)}

def sync_settlement_recovery(db:Session, facility_id:UUID, actor_id:UUID, limit:int=200):
    recs=db.scalars(select(SettlementReconciliation).join(
        SettlementBatch,SettlementBatch.id==SettlementReconciliation.batch_id
    ).where(
        SettlementBatch.facility_id==facility_id,
        SettlementReconciliation.difference < 0,
        SettlementReconciliation.recovery_status.in_(["OPEN","IN_PROGRESS"])
    ).order_by(SettlementReconciliation.id).limit(max(1,min(limit,500)))).all()
    opened=0
    for rec in recs:
        existing=db.scalar(select(RevenueRecoveryCase).where(
            RevenueRecoveryCase.reconciliation_id==rec.id,
            RevenueRecoveryCase.status.in_(["OPEN","IN_PROGRESS","DISPUTED"])
        ))
        if existing:
            continue
        try:
            open_recovery(db,rec.id,facility_id,"CONTRACT_CASH_VARIANCE","HIGH","Automated Phase 75 recovery intake from settlement shortfall.",actor_id)
            opened+=1
        except ValueError:
            db.rollback()
    record_audit(db,actor_id,"SYNC_CONTRACT_CASH_RECOVERY","revenue_recovery_cases",str(facility_id),{"opened":opened,"candidates":len(recs)})
    return {"opened":opened,"candidates":len(recs)}

def close_loop(db:Session, facility_id:UUID, actor_id:UUID, limit:int=200):
    work=sync_guardrail_work(db,facility_id,actor_id,limit)
    recovery=sync_settlement_recovery(db,facility_id,actor_id,limit)
    return {"work_queue":work,"recovery":recovery}
