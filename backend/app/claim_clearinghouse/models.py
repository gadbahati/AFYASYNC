from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ClearinghouseRoute(Base):
    __tablename__ = "clearinghouse_routes"
    __table_args__ = (UniqueConstraint("facility_id","payer_id","source_type","adapter_code",name="uq_clearinghouse_route"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    payer_id: Mapped[UUID | None] = mapped_column(ForeignKey("payers.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    adapter_code: Mapped[str] = mapped_column(String(80), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    supports_submission: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supports_callback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    configuration: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ClearinghouseCase(Base):
    __tablename__ = "clearinghouse_cases"
    __table_args__ = (UniqueConstraint("facility_id","idempotency_key",name="uq_clearinghouse_case_idempotency"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_number: Mapped[str] = mapped_column(String(90), unique=True, index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    claim_id: Mapped[UUID | None] = mapped_column(ForeignKey("claims.id", ondelete="SET NULL"), index=True)
    invoice_id: Mapped[UUID | None] = mapped_column(ForeignKey("invoices.id", ondelete="SET NULL"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    payer_id: Mapped[UUID | None] = mapped_column(ForeignKey("payers.id", ondelete="SET NULL"), index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    adapter_code: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="INTAKE", index=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), nullable=False)
    claim_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, default=0)
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, default=0)
    external_reference: Mapped[str | None] = mapped_column(String(180), index=True)
    denial_code: Mapped[str | None] = mapped_column(String(80))
    denial_category: Mapped[str | None] = mapped_column(String(60))
    denial_message: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ClearinghouseEvent(Base):
    __tablename__ = "clearinghouse_events"
    __table_args__ = (Index("ix_clearinghouse_events_case", "case_id", "created_at"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("clearinghouse_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str | None] = mapped_column(String(40))
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    message: Mapped[str | None] = mapped_column(Text)
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ClearinghouseDenialCode(Base):
    __tablename__ = "clearinghouse_denial_codes"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class ClearinghouseRemittance(Base):
    __tablename__ = "clearinghouse_remittances"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("clearinghouse_cases.id", ondelete="RESTRICT"), nullable=False, index=True)
    external_reference: Mapped[str | None] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RECEIVED")
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, default=0)
    patient_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    event_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB)
