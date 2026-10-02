from datetime import datetime
from uuid import UUID,uuid4
from sqlalchemy import DateTime,ForeignKey,Index,String,Text,func
from sqlalchemy.dialects.postgresql import UUID as PGUUID,JSONB
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base

class ContractExecutionApproval(Base):
    __tablename__="contract_execution_approvals"
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    facility_id:Mapped[UUID]=mapped_column(ForeignKey("facilities.id",ondelete="CASCADE"),nullable=False,index=True)
    contract_id:Mapped[UUID]=mapped_column(ForeignKey("provider_network_contracts.id",ondelete="CASCADE"),nullable=False,index=True)
    negotiation_case_id:Mapped[UUID|None]=mapped_column(ForeignKey("payer_negotiation_cases.id",ondelete="SET NULL"))
    status:Mapped[str]=mapped_column(String(25),nullable=False,default="PENDING",index=True)
    requested_by:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="RESTRICT"))
    reviewed_by:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="RESTRICT"))
    requested_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    reviewed_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    requested_terms:Mapped[dict|None]=mapped_column(JSONB)
    review_notes:Mapped[str|None]=mapped_column(Text)

class ContractExecutionEvent(Base):
    __tablename__="contract_execution_events"
    __table_args__=(Index("ix_contract_execution_events_contract_created","contract_id","created_at"),)
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    contract_id:Mapped[UUID]=mapped_column(ForeignKey("provider_network_contracts.id",ondelete="CASCADE"),nullable=False,index=True)
    approval_id:Mapped[UUID|None]=mapped_column(ForeignKey("contract_execution_approvals.id",ondelete="SET NULL"))
    event_type:Mapped[str]=mapped_column(String(50),nullable=False)
    actor_id:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="RESTRICT"))
    notes:Mapped[str|None]=mapped_column(Text)
    metadata:Mapped[dict|None]=mapped_column(JSONB)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
