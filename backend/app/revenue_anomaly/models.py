from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RevenueAnomalyCase(Base):
    __tablename__ = "revenue_anomaly_cases"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_number: Mapped[str] = mapped_column(String(90), unique=True, index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    anomaly_type: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM", index=True)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)
    claim_id: Mapped[UUID | None] = mapped_column(ForeignKey("claims.id", ondelete="SET NULL"), index=True)
    invoice_id: Mapped[UUID | None] = mapped_column(ForeignKey("invoices.id", ondelete="SET NULL"), index=True)
    patient_id: Mapped[UUID | None] = mapped_column(ForeignKey("persons.id", ondelete="SET NULL"), index=True)
    payer_id: Mapped[UUID | None] = mapped_column(ForeignKey("payers.id", ondelete="SET NULL"), index=True)
    recovery_case_id: Mapped[UUID | None] = mapped_column(ForeignKey("revenue_recovery_cases.id", ondelete="SET NULL"), index=True)
    amount_at_risk: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    fingerprint: Mapped[str] = mapped_column(String(180), index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RevenueAnomalyEvent(Base):
    __tablename__ = "revenue_anomaly_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(ForeignKey("revenue_anomaly_cases.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
