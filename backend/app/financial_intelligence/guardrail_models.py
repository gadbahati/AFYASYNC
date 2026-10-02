from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ContractComplianceGuardrail(Base):
    __tablename__="contract_compliance_guardrails"
    __table_args__=(
        Index("ix_contract_guardrail_status","status","severity"),
        Index("ix_contract_guardrail_type","guardrail_type"),
    )
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    facility_id:Mapped[UUID]=mapped_column(ForeignKey("facilities.id",ondelete="CASCADE"),nullable=False,index=True)
    contract_id:Mapped[UUID|None]=mapped_column(ForeignKey("provider_network_contracts.id",ondelete="SET NULL"),index=True)
    claim_id:Mapped[UUID|None]=mapped_column(ForeignKey("claims.id",ondelete="SET NULL"),index=True)
    payer_id:Mapped[UUID|None]=mapped_column(ForeignKey("payers.id",ondelete="SET NULL"),index=True)
    guardrail_type:Mapped[str]=mapped_column(String(50),nullable=False)
    severity:Mapped[str]=mapped_column(String(20),nullable=False,default="MEDIUM")
    status:Mapped[str]=mapped_column(String(30),nullable=False,default="OPEN")
    title:Mapped[str]=mapped_column(String(220),nullable=False)
    expected_amount:Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False,default=0)
    actual_amount:Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False,default=0)
    amount_at_risk:Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False,default=0)
    detail:Mapped[str|None]=mapped_column(Text)
    evidence:Mapped[dict|None]=mapped_column(JSONB)
    assigned_to:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"))
    resolved_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)

class ContractComplianceGuardrailEvent(Base):
    __tablename__="contract_compliance_guardrail_events"
    __table_args__=(Index("ix_contract_guardrail_events_guardrail","guardrail_id","created_at"),)
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    guardrail_id:Mapped[UUID]=mapped_column(ForeignKey("contract_compliance_guardrails.id",ondelete="CASCADE"),nullable=False,index=True)
    event_type:Mapped[str]=mapped_column(String(60),nullable=False)
    from_status:Mapped[str|None]=mapped_column(String(30))
    to_status:Mapped[str|None]=mapped_column(String(30))
    actor_id:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"))
    note:Mapped[str|None]=mapped_column(Text)
    metadata_json:Mapped[dict|None]=mapped_column(JSONB)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
