from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    claim_id: Mapped[str] = mapped_column(String(70), unique=True, index=True)
    invoice_id: Mapped[UUID] = mapped_column(ForeignKey("invoices.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[UUID] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    payer_id: Mapped[UUID] = mapped_column(ForeignKey("payers.id", ondelete="RESTRICT"), index=True)
    claim_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ClaimItem(Base):
    __tablename__ = "claim_items"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id", ondelete="RESTRICT"), index=True)
    charge_id: Mapped[UUID] = mapped_column(ForeignKey("charges.id", ondelete="RESTRICT"))
    service_code: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)


class ClaimResponse(Base):
    __tablename__ = "claim_responses"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id", ondelete="RESTRICT"), index=True)
    external_reference: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    response_code: Mapped[str | None] = mapped_column(String(80))
    response_message: Mapped[str | None] = mapped_column(String(500))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Reconciliation(Base):
    __tablename__ = "reconciliations"
    __table_args__ = (UniqueConstraint("claim_id", name="uq_reconciliation_claim"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    claim_id: Mapped[UUID] = mapped_column(ForeignKey("claims.id", ondelete="RESTRICT"), index=True)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    received_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    difference: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    reconciled_by: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
