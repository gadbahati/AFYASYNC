from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class FinancingPreauthorization(Base):
    __tablename__ = "financing_preauthorizations"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    authorization_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True)
    coverage_id: Mapped[UUID] = mapped_column(ForeignKey("coverage.id", ondelete="RESTRICT"), nullable=False, index=True)
    payer_id: Mapped[UUID] = mapped_column(ForeignKey("payers.id", ondelete="RESTRICT"), nullable=False, index=True)
    service_code: Mapped[str | None] = mapped_column(String(80), index=True)
    service_type: Mapped[str | None] = mapped_column(String(60), index=True)
    requested_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    approved_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING", index=True)
    decision_reason: Mapped[str | None] = mapped_column(String(120))
    external_reference: Mapped[str | None] = mapped_column(String(150))
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
