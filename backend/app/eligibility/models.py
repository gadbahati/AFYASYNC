from __future__ import annotations
from datetime import date, datetime
from uuid import UUID, uuid4
from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class EligibilityDecision(Base):
    __tablename__ = "eligibility_decisions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True)
    payer_id: Mapped[UUID | None] = mapped_column(ForeignKey("payers.id", ondelete="SET NULL"), index=True)
    payer_plan_id: Mapped[UUID | None] = mapped_column(ForeignKey("payer_plans.id", ondelete="SET NULL"), index=True)
    service_code: Mapped[str | None] = mapped_column(String(80), index=True)
    service_type: Mapped[str | None] = mapped_column(String(60), index=True)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)  # ELIGIBLE | INELIGIBLE | CONDITIONAL | UNKNOWN
    reason_code: Mapped[str] = mapped_column(String(60), nullable=False)
    coverage_id: Mapped[UUID | None] = mapped_column(ForeignKey("coverage.id", ondelete="SET NULL"), index=True)
    estimated_payer_amount: Mapped[float] = mapped_column(Numeric(14,2), nullable=False, default=0)
    estimated_patient_amount: Mapped[float] = mapped_column(Numeric(14,2), nullable=False, default=0)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    evidence: Mapped[dict | None] = mapped_column(JSONB)

class FinancingPersonIdentifier(Base):
    __tablename__ = "financing_person_identifiers"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True)
    identifier_type: Mapped[str] = mapped_column(String(40), nullable=False)  # AFYA_ID | PAYER_MEMBER | NATIONAL_ID_HASH | PHONE
    identifier_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    payer_id: Mapped[UUID | None] = mapped_column(ForeignKey("payers.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
