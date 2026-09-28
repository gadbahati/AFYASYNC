from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ExchangeMessage(Base):
    __tablename__="health_exchange_messages"
    __table_args__=(UniqueConstraint("message_id",name="uq_health_exchange_message_id"),Index("ix_health_exchange_message_status","status","created_at"),Index("ix_health_exchange_patient","patient_id","created_at"),Index("ix_health_exchange_type","message_type","created_at"))
    id: Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    message_id: Mapped[str]=mapped_column(String(100),nullable=False)
    message_type: Mapped[str]=mapped_column(String(60),nullable=False)
    patient_id: Mapped[UUID|None]=mapped_column(ForeignKey("persons.id",ondelete="SET NULL"),index=True)
    source_facility_id: Mapped[UUID|None]=mapped_column(ForeignKey("facilities.id",ondelete="SET NULL"),index=True)
    destination_facility_id: Mapped[UUID|None]=mapped_column(ForeignKey("facilities.id",ondelete="SET NULL"),index=True)
    correlation_id: Mapped[str|None]=mapped_column(String(100),index=True)
    schema_version: Mapped[str]=mapped_column(String(30),nullable=False,default="1.0")
    payload: Mapped[dict]=mapped_column(JSONB,nullable=False)
    status: Mapped[str]=mapped_column(String(30),nullable=False,default="ACCEPTED",index=True)
    error_code: Mapped[str|None]=mapped_column(String(80))
    error_message: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),index=True)
    processed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
