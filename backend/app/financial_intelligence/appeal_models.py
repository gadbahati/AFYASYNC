from datetime import datetime
from uuid import UUID,uuid4
from sqlalchemy import DateTime,ForeignKey,Index,String,Text,func
from sqlalchemy.dialects.postgresql import JSONB,UUID as PGUUID
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base
class DenialAppeal(Base):
    __tablename__="denial_appeals"
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    facility_id:Mapped[UUID]=mapped_column(ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False,index=True)
    clearinghouse_case_id:Mapped[UUID]=mapped_column(ForeignKey("clearinghouse_cases.id",ondelete="CASCADE"),nullable=False,index=True)
    resolution_case_id:Mapped[UUID|None]=mapped_column(ForeignKey("revenue_resolution_cases.id",ondelete="SET NULL"))
    appeal_number:Mapped[str]=mapped_column(String(90),unique=True,index=True)
    status:Mapped[str]=mapped_column(String(30),nullable=False,default="DRAFT",index=True)
    assigned_to:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"))
    due_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    submitted_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    resolved_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    external_reference:Mapped[str|None]=mapped_column(String(180))
    grounds:Mapped[str|None]=mapped_column(Text)
    evidence_checklist:Mapped[dict|None]=mapped_column(JSONB)
    submission_notes:Mapped[str|None]=mapped_column(Text)
    outcome:Mapped[str|None]=mapped_column(String(40))
    outcome_notes:Mapped[str|None]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)
class DenialAppealEvent(Base):
    __tablename__="denial_appeal_events"
    __table_args__=(Index("ix_denial_appeal_events_appeal","appeal_id","created_at"),)
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    appeal_id:Mapped[UUID]=mapped_column(ForeignKey("denial_appeals.id",ondelete="CASCADE"),nullable=False,index=True)
    event_type:Mapped[str]=mapped_column(String(50),nullable=False)
    from_status:Mapped[str|None]=mapped_column(String(30))
    to_status:Mapped[str|None]=mapped_column(String(30))
    actor_id:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"))
    note:Mapped[str|None]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
