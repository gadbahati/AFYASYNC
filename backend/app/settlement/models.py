from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class SettlementObligation(Base):
    __tablename__ = "settlement_obligations"
    __table_args__ = (UniqueConstraint("claim_id", name="uq_settlement_obligation_claim"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    obligation_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    payer_id: Mapped[UUID] = mapped_column(ForeignKey("payers.id", ondelete="RESTRICT"), index=True)
    submitted_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    patient_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="READY", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SettlementBatch(Base):
    __tablename__ = "settlement_batches"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    batch_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    payer_id: Mapped[UUID] = mapped_column(ForeignKey("payers.id", ondelete="RESTRICT"), index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class ProviderPayment(Base):
    __tablename__ = "provider_payments"
    __table_args__ = (UniqueConstraint("obligation_id", name="uq_provider_payment_obligation"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    payment_reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("settlement_batches.id", ondelete="RESTRICT"), index=True)
    obligation_id: Mapped[UUID] = mapped_column(ForeignKey("settlement_obligations.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    payer_id: Mapped[UUID] = mapped_column(ForeignKey("payers.id", ondelete="RESTRICT"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    method: Mapped[str] = mapped_column(String(40), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RECORDED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class SettlementReconciliation(Base):
    __tablename__ = "settlement_reconciliations"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("settlement_batches.id", ondelete="RESTRICT"), index=True)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    received_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    difference: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    reconciled_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    variance_type: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(String(1000))
    recovery_status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")

class SettlementLedgerEntry(Base):
    __tablename__ = "settlement_ledger_entries"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    batch_id: Mapped[UUID] = mapped_column(ForeignKey("settlement_batches.id", ondelete="RESTRICT"), index=True)
    obligation_id: Mapped[UUID | None] = mapped_column(ForeignKey("settlement_obligations.id", ondelete="SET NULL"), index=True)
    entry_type: Mapped[str] = mapped_column(String(40), nullable=False)
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, default=0)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(14,2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    reference: Mapped[str] = mapped_column(String(150), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
