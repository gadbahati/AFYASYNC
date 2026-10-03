from datetime import datetime,timedelta,timezone
from uuid import UUID
from sqlalchemy import select

from datetime import datetime,timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.financial_intelligence.work_queue import CollectionWorkItem
from app.financial_intelligence.guardrail_models import ContractComplianceGuardrail
from app.financial_intelligence.resolution_models import RevenueResolutionCase
from app.settlement.recovery import RevenueRecoveryCase

LEVELS=["LOW","MEDIUM","HIGH","CRITICAL"]

def _next_priority(value:str):
    try:i=LEVELS.index(value)
    except ValueError:i=0
    return LEVELS[min(i+1,len(LEVELS)-1)]

def orchestrate_revenue_workflow(db:Session,facility_id:UUID,actor_id:UUID,limit:int=50):
    sync=automate_revenue_actions(db,facility_id,actor_id,limit)
    now=datetime.now(timezone.utc)
    overdue=list(db.scalars(select(CollectionWorkItem).where(
        CollectionWorkItem.facility_id==facility_id,
        CollectionWorkItem.status.in_(["OPEN","IN_PROGRESS","SNOOZED"]),
        CollectionWorkItem.due_at.is_not(None),
        CollectionWorkItem.due_at<now,
    )).all())
    escalated=0
    assigned=0
    for item in overdue:
        old_priority=item.priority
        item.priority=_next_priority(item.priority)
        if item.status=="OPEN":
            item.status="IN_PROGRESS"
        if item.assigned_to is None:
            item.assigned_to=actor_id
            assigned+=1
        item.note=(item.note or "")+f" Overdue orchestration escalation at {now.isoformat()}."
        escalated+=1
    db.flush()
    record_audit(db,actor_id,"ORCHESTRATE_REVENUE_WORKFLOW","collection_work_items",str(facility_id),{
        "sync_created":sync["created"],"sync_updated":sync["updated"],
        "overdue_escalated":escalated,"auto_assigned":assigned
    })
    db.commit()
    return {"sync":sync,"overdue_escalated":escalated,"auto_assigned":assigned,
            "note":"Workflow orchestration refreshes prioritized actions and escalates overdue active work without creating duplicate records."}

from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.financial_intelligence.revenue_action_priorities import revenue_action_priorities
from app.financial_intelligence.work_queue import CollectionWorkItem

ACTION_MAP={
    "GUARDRAIL":("REVENUE_ACTION_GUARDRAIL","REVIEW_CONTRACT_COMPLIANCE"),
    "RECOVERY":("REVENUE_ACTION_RECOVERY","FOLLOW_UP_RECOVERY"),
    "RESOLUTION":("REVENUE_ACTION_RESOLUTION","ESCALATE_RESOLUTION"),
}

def automate_revenue_actions(db:Session,facility_id:UUID,actor_id:UUID,limit:int=50):
    data=revenue_action_priorities(db,facility_id,limit)
    created=updated=skipped=0
    for item in data["items"]:
        source_type,expected_action=ACTION_MAP.get(item["source"],("REVENUE_ACTION",""))
        if item["recommended_action"]!=expected_action:
            skipped+=1
            continue
        source_id=UUID(item["source_id"])
        priority="CRITICAL" if item["priority_score"]>=90 else "HIGH" if item["priority_score"]>=70 else "MEDIUM" if item["priority_score"]>=40 else "LOW"
        due_days=1 if priority=="CRITICAL" else 2 if priority=="HIGH" else 5 if priority=="MEDIUM" else 10
        title=f"{item['recommended_action'].replace('_',' ').title()}: {item['title']}"
        note=f"Automated from revenue action priority score {item['priority_score']}. Source: {item['source']}."
        existing=db.scalar(select(CollectionWorkItem).where(
            CollectionWorkItem.facility_id==facility_id,
            CollectionWorkItem.source_type==source_type,
            CollectionWorkItem.source_id==source_id,
            CollectionWorkItem.status!="DONE",
        ))
        if existing:
            existing.priority=priority
            existing.outstanding_amount=item["amount"]
            existing.title=title
            existing.note=note
            existing.due_at=datetime.now(timezone.utc)+timedelta(days=due_days)
            updated+=1
            continue
        db.add(CollectionWorkItem(
            facility_id=facility_id,
            source_type=source_type,
            source_id=source_id,
            title=title,
            priority=priority,
            status="OPEN",
            due_at=datetime.now(timezone.utc)+timedelta(days=due_days),
            outstanding_amount=item["amount"],
            note=note,
        ))
        created+=1
    db.flush()
    record_audit(db,actor_id,"AUTOMATE_REVENUE_ACTIONS","collection_work_items",str(facility_id),{
        "created":created,"updated":updated,"skipped":skipped,"candidates":len(data["items"])
    })
    db.commit()
    return {"created":created,"updated":updated,"skipped":skipped,"candidates":len(data["items"]),"note":"Idempotent synchronization; active work items are updated rather than duplicated."}

def reconcile_revenue_work(db:Session,facility_id:UUID,actor_id:UUID,limit:int=200):
    items=list(db.scalars(select(CollectionWorkItem).where(CollectionWorkItem.facility_id==facility_id,CollectionWorkItem.status.in_(["OPEN","IN_PROGRESS","SNOOZED"])).order_by(CollectionWorkItem.created_at.asc()).limit(max(1,min(limit,500)))).all())
    closed=0
    for item in items:
        resolved=False
        if item.source_type in {"CONTRACT_GUARDRAIL","REVENUE_ACTION_GUARDRAIL"}:
            source=db.get(ContractComplianceGuardrail,item.source_id)
            resolved=source is not None and source.status in {"RESOLVED","DISMISSED"}
        elif item.source_type=="REVENUE_ACTION_RESOLUTION":
            source=db.get(RevenueResolutionCase,item.source_id)
            resolved=source is not None and source.status in {"RESOLVED","CLOSED"}
        elif item.source_type=="REVENUE_ACTION_RECOVERY":
            source=db.get(RevenueRecoveryCase,item.source_id)
            resolved=source is not None and source.status in {"RECOVERED","CLOSED","WRITTEN_OFF"}
        if resolved:
            item.status="DONE"
            item.outstanding_amount=0
            item.note=(item.note or "")+" Automatically closed after source lifecycle verification."
            closed+=1
    db.flush()
    record_audit(db,actor_id,"RECONCILE_REVENUE_WORK","collection_work_items",str(facility_id),{"checked":len(items),"closed":closed})
    db.commit()
    return {"checked":len(items),"closed":closed,"note":"Work closes only after the underlying guardrail, recovery, or resolution record reaches a terminal state."}
