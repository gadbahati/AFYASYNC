from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
class RevenueResolutionCase(Base):
    __tablename__="revenue_resolution_cases"
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    case_number:Mapped[str]=mapped_column(String(90),unique=True,index=True)
    facility_id:Mapped[UUID]=mapped_column(ForeignKey("facilities.id",ondelete="RESTRICT"),index=True)
    source_type:Mapped[str]=mapped_column(String(40),nullable=False)
    source_id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),nullable=False)
    claim_id:Mapped[UUID|None]=mapped_column(ForeignKey("claims.id",ondelete="SET NULL"),index=True)
    payer_id:Mapped[UUID|None]=mapped_column(ForeignKey("payers.id",ondelete="SET NULL"),index=True)
    patient_id:Mapped[UUID|None]=mapped_column(ForeignKey("persons.id",ondelete="SET NULL"),index=True)
    title:Mapped[str]=mapped_column(String(220),nullable=False)
    priority:Mapped[str]=mapped_column(String(20),nullable=False,default="MEDIUM",index=True)
    status:Mapped[str]=mapped_column(String(30),nullable=False,default="OPEN",index=True)
    assigned_to:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"))
    due_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    amount_at_risk:Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False,default=0)
    root_cause:Mapped[str|None]=mapped_column(String(80))
    resolution_action:Mapped[str|None]=mapped_column(Text)
    external_reference:Mapped[str|None]=mapped_column(String(180))
    notes:Mapped[str|None]=mapped_column(Text)
    resolved_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)
class RevenueResolutionEvent(Base):
    __tablename__="revenue_resolution_events"
    __table_args__=(Index("ix_revenue_resolution_events_case","case_id","created_at"),)
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    case_id:Mapped[UUID]=mapped_column(ForeignKey("revenue_resolution_cases.id",ondelete="CASCADE"),nullable=False,index=True)
    event_type:Mapped[str]=mapped_column(String(60),nullable=False)
    from_status:Mapped[str|None]=mapped_column(String(30))
    to_status:Mapped[str|None]=mapped_column(String(30))
    actor_id:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"))
    note:Mapped[str|None]=mapped_column(Text)
    metadata_json:Mapped[dict|None]=mapped_column(JSONB)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
