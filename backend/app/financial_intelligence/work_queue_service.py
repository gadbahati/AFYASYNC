from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.financial_intelligence.work_queue import CollectionWorkItem
from app.financial_intelligence.service import collection_priorities

STATUSES={"OPEN","IN_PROGRESS","SNOOZED","DONE"}
PRIORITIES={"LOW","MEDIUM","HIGH","CRITICAL","NORMAL"}

def sync_collection_queue(db:Session, facility_id:UUID, actor_id:UUID, limit:int=100):
    data=collection_priorities(db,facility_id,limit)
    created=0
    for item in data["actions"]:
        source_type=item["type"]
        source_id=UUID(item.get("claim_id") or item.get("invoice_id"))
        existing=db.scalar(select(CollectionWorkItem).where(
            CollectionWorkItem.facility_id==facility_id,
            CollectionWorkItem.source_type==source_type,
            CollectionWorkItem.source_id==source_id,
            CollectionWorkItem.status!="DONE",
        ))
        if existing:
            existing.outstanding_amount=item["outstanding"]
            existing.priority=item["priority"]
            existing.title=f"{source_type.replace('_',' ').title()}: collection follow-up"
            continue
        due= datetime.now(timezone.utc)+timedelta(days=1 if item["priority"]=="CRITICAL" else 3 if item["priority"]=="HIGH" else 7)
        db.add(CollectionWorkItem(
            facility_id=facility_id,source_type=source_type,source_id=source_id,
            title=f"{source_type.replace('_',' ').title()}: collection follow-up",
            priority=item["priority"],status="OPEN",due_at=due,
            outstanding_amount=item["outstanding"],note=item["action"]))
        created+=1
    db.flush()
    record_audit(db,actor_id,"SYNC_COLLECTION_WORK_QUEUE","collection_work_items",str(facility_id),{"created":created,"total_candidates":len(data["actions"])})
    db.commit()
    return {"created":created,"summary":data["summary"]}

def list_work(db:Session,facility_id:UUID,status:str|None=None,limit:int=100):
    q=select(CollectionWorkItem).where(CollectionWorkItem.facility_id==facility_id)
    if status: q=q.where(CollectionWorkItem.status==status)
    return db.scalars(q.order_by(CollectionWorkItem.priority.desc(),CollectionWorkItem.due_at.asc()).limit(max(1,min(limit,500)))).all()

def update_work(db:Session,facility_id:UUID,item_id:UUID,status:str,assigned_to:UUID|None,due_at:datetime|None,note:str|None,actor_id:UUID):
    item=db.get(CollectionWorkItem,item_id)
    if item is None: raise ValueError("WORK_ITEM_NOT_FOUND")
    if item.facility_id!=facility_id: raise ValueError("FACILITY_ACCESS_DENIED")
    if status not in STATUSES: raise ValueError("INVALID_WORK_STATUS")
    if assigned_to is not None: item.assigned_to=assigned_to
    if due_at is not None: item.due_at=due_at
    if note is not None: item.note=note
    item.status=status
    record_audit(db,actor_id,"UPDATE_COLLECTION_WORK_ITEM","collection_work_item",str(item.id),{"status":status,"assigned_to":str(assigned_to) if assigned_to else None})
    db.commit(); db.refresh(item); return item

def queue_overview(db:Session,facility_id:UUID):
    rows=db.execute(select(CollectionWorkItem.status,func.count(CollectionWorkItem.id),func.coalesce(func.sum(CollectionWorkItem.outstanding_amount),0)).where(CollectionWorkItem.facility_id==facility_id).group_by(CollectionWorkItem.status)).all()
    return {"statuses":{str(s):{"count":int(c),"outstanding_amount":float(a or 0)} for s,c,a in rows}}
