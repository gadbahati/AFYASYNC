from datetime import date, datetime
from uuid import UUID, uuid4
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class BenefitRuleVersion(Base):
    __tablename__ = "benefit_rule_versions"
    __table_args__ = (UniqueConstraint("benefit_package_id","service_code","service_type","version","name", name="uq_benefit_rule_version"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    benefit_package_id: Mapped[UUID] = mapped_column(ForeignKey("benefit_packages.id", ondelete="RESTRICT"), nullable=False, index=True)
    payer_id: Mapped[UUID] = mapped_column(ForeignKey("payers.id", ondelete="RESTRICT"), nullable=False, index=True)
    payer_plan_id: Mapped[UUID | None] = mapped_column(ForeignKey("payer_plans.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    service_code: Mapped[str | None] = mapped_column(String(80), index=True)
    service_type: Mapped[str | None] = mapped_column(String(60), index=True)
    tariff_amount: Mapped[float | None] = mapped_column(Numeric(14,2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    payer_percent: Mapped[float] = mapped_column(Numeric(5,2), nullable=False, default=100)
    fixed_patient_copay: Mapped[float] = mapped_column(Numeric(14,2), nullable=False, default=0)
    max_covered_amount: Mapped[float | None] = mapped_column(Numeric(14,2))
    annual_limit_amount: Mapped[float | None] = mapped_column(Numeric(14,2))
    is_excluded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_preauth: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    required_documents: Mapped[dict | list | None] = mapped_column(JSONB)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
