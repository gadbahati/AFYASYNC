from datetime import datetime,timedelta,timezone
from uuid import UUID
from sqlalchemy import select
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
