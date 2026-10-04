from datetime import datetime
from uuid import UUID,uuid4
from sqlalchemy import DateTime,ForeignKey,Index,String,Text,func
from sqlalchemy.dialects.postgresql import UUID as PGUUID,JSONB
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base

class PayerNegotiationCase(Base):
    __tablename__="payer_negotiation_cases"
    __table_args__=(Index("ix_payer_negotiation_contract_status","contract_id","status"),)
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    facility_id:Mapped[UUID]=mapped_column(ForeignKey("facilities.id",ondelete="CASCADE"),nullable=False,index=True)
    contract_id:Mapped[UUID]=mapped_column(ForeignKey("provider_network_contracts.id",ondelete="CASCADE"),nullable=False,index=True)
    case_number:Mapped[str]=mapped_column(String(80),nullable=False,unique=True)
    status:Mapped[str]=mapped_column(String(30),nullable=False,default="DRAFT",index=True)
    owner_id:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="RESTRICT"))
    due_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    objective:Mapped[str|None]=mapped_column(Text)
    opening_position:Mapped[dict|None]=mapped_column(JSONB)
    target_position:Mapped[dict|None]=mapped_column(JSONB)
    evidence_snapshot:Mapped[dict|None]=mapped_column(JSONB)
    proposed_terms:Mapped[dict|None]=mapped_column(JSONB)
    accepted_terms:Mapped[dict|None]=mapped_column(JSONB)
    notes:Mapped[str|None]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
    closed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))

class PayerNegotiationItem(Base):
    __tablename__="payer_negotiation_items"
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    case_id:Mapped[UUID]=mapped_column(ForeignKey("payer_negotiation_cases.id",ondelete="CASCADE"),nullable=False,index=True)
    item_type:Mapped[str]=mapped_column(String(40),nullable=False)
    title:Mapped[str]=mapped_column(String(200),nullable=False)
    current_value:Mapped[dict|None]=mapped_column(JSONB)
    requested_value:Mapped[dict|None]=mapped_column(JSONB)
    rationale:Mapped[str|None]=mapped_column(Text)
    priority:Mapped[str]=mapped_column(String(20),nullable=False,default="MEDIUM")
    status:Mapped[str]=mapped_column(String(25),nullable=False,default="PROPOSED",index=True)
    external_response:Mapped[str|None]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())

class PayerNegotiationEvent(Base):
    __tablename__="payer_negotiation_events"
    __table_args__=(Index("ix_payer_negotiation_events_case_created","case_id","created_at"),)
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    case_id:Mapped[UUID]=mapped_column(ForeignKey("payer_negotiation_cases.id",ondelete="CASCADE"),nullable=False,index=True)
    event_type:Mapped[str]=mapped_column(String(50),nullable=False)
    from_status:Mapped[str|None]=mapped_column(String(30))
    to_status:Mapped[str|None]=mapped_column(String(30))
    actor_id:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="RESTRICT"))
    note:Mapped[str|None]=mapped_column(Text)
    event_metadata:Mapped[dict|None]=mapped_column("metadata",JSONB)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
