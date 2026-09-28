from datetime import datetime,timezone
from uuid import uuid4
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.health_exchange.models import ExchangeMessage
class HealthExchangeError(ValueError): pass
ALLOWED={"ACCEPTED","PROCESSING","PROCESSED","REJECTED","FAILED"}
def publish(db,payload,actor):
    old=db.scalar(select(ExchangeMessage).where(ExchangeMessage.message_id==payload["message_id"]))
    if old: raise HealthExchangeError("MESSAGE_ID_EXISTS")
    row=ExchangeMessage(**payload,status="ACCEPTED");db.add(row);db.flush()
    record_audit(db,action="PUBLISH_HEALTH_EXCHANGE_MESSAGE",resource_type="HEALTH_EXCHANGE_MESSAGE",resource_id=str(row.id),result="SUCCESS",user_id=actor,facility_id=row.source_facility_id,patient_id=row.patient_id,metadata={"message_type":row.message_type,"schema_version":row.schema_version},commit=False)
    db.commit();db.refresh(row);return row
def list_messages(db,message_type=None,patient_id=None,status=None,limit=100):
    q=select(ExchangeMessage).order_by(ExchangeMessage.created_at.desc())
    if message_type:q=q.where(ExchangeMessage.message_type==message_type)
    if patient_id:q=q.where(ExchangeMessage.patient_id==patient_id)
    if status:q=q.where(ExchangeMessage.status==status)
    return list(db.scalars(q.limit(min(max(limit,1),200))))
def update_status(db,message_id,status,actor):
    if status not in ALLOWED:raise HealthExchangeError("INVALID_STATUS")
    row=db.scalar(select(ExchangeMessage).where(ExchangeMessage.message_id==message_id))
    if not row:raise HealthExchangeError("MESSAGE_NOT_FOUND")
    row.status=status
    if status in {"PROCESSED","FAILED","REJECTED"}:row.processed_at=datetime.now(timezone.utc)
    record_audit(db,action="UPDATE_HEALTH_EXCHANGE_MESSAGE",resource_type="HEALTH_EXCHANGE_MESSAGE",resource_id=str(row.id),result="SUCCESS",user_id=actor,facility_id=row.source_facility_id,patient_id=row.patient_id,metadata={"status":status},commit=False)
    db.commit();db.refresh(row);return row
def overview(db):
    total=db.scalar(select(func.count()).select_from(ExchangeMessage)) or 0
    accepted=db.scalar(select(func.count()).select_from(ExchangeMessage).where(ExchangeMessage.status=="ACCEPTED")) or 0
    processed=db.scalar(select(func.count()).select_from(ExchangeMessage).where(ExchangeMessage.status=="PROCESSED")) or 0
    failed=db.scalar(select(func.count()).select_from(ExchangeMessage).where(ExchangeMessage.status=="FAILED")) or 0
    types=list(db.scalars(select(ExchangeMessage.message_type,func.count()).group_by(ExchangeMessage.message_type).order_by(func.count().desc())))
    return {"messages":total,"accepted":accepted,"processed":processed,"failed":failed,"message_types":[{"type":x[0],"count":x[1]} for x in types]}
