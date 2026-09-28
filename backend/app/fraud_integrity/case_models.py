from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class FraudIntegrityCase(Base):
    __tablename__ = "fraud_integrity_cases"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    claim_id: Mapped[UUID | None] = mapped_column(ForeignKey("claims.id", ondelete="SET NULL"), index=True)
    patient_id: Mapped[UUID | None] = mapped_column(ForeignKey("persons.id", ondelete="SET NULL"), index=True)
    payer_id: Mapped[UUID | None] = mapped_column(ForeignKey("payers.id", ondelete="SET NULL"), index=True)
    signal_code: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM", index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    assigned_to: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
