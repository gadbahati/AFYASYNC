from datetime import datetime
from uuid import UUID,uuid4
from sqlalchemy import Boolean,DateTime,ForeignKey,Index,Integer,Text,String,UniqueConstraint,func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base
class PayerSLAPolicy(Base):
    __tablename__="payer_sla_policies"
    __table_args__=(UniqueConstraint("facility_id","payer_id",name="uq_payer_sla_policy_facility_payer"),Index("ix_payer_sla_policies_facility","facility_id","active"),Index("ix_payer_sla_policies_payer","payer_id","active"))
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4); payer_id:Mapped[UUID]=mapped_column(ForeignKey("payers.id",ondelete="CASCADE"),nullable=False); facility_id:Mapped[UUID]=mapped_column(ForeignKey("facilities.id",ondelete="CASCADE"),nullable=False)
    denial_response_hours:Mapped[int]=mapped_column(Integer,nullable=False,default=48); resolution_hours:Mapped[int]=mapped_column(Integer,nullable=False,default=168); appeal_hours:Mapped[int]=mapped_column(Integer,nullable=False,default=120); escalation_hours:Mapped[int]=mapped_column(Integer,nullable=False,default=24)
    active:Mapped[bool]=mapped_column(Boolean,nullable=False,default=True); notes:Mapped[str|None]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False); updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)
class RevenueResolutionSLAEvent(Base):
    __tablename__="revenue_resolution_sla_events"; __table_args__=(Index("ix_revenue_resolution_sla_events_case","case_id","created_at"),)
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4); case_id:Mapped[UUID]=mapped_column(ForeignKey("revenue_resolution_cases.id",ondelete="CASCADE"),nullable=False)
    event_type:Mapped[str]=mapped_column(String(60),nullable=False); from_level:Mapped[int|None]=mapped_column(Integer); to_level:Mapped[int|None]=mapped_column(Integer); note:Mapped[str|None]=mapped_column(Text); actor_id:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL")); created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
