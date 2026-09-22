"""Medication safety catalogue flags."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MedicationSafetyFlag(Base):
    """Per-medication safety attributes used at prescribe-time."""

    __tablename__ = "medication_safety_flags"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    medication_id: Mapped[UUID] = mapped_column(
        ForeignKey("medications.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    high_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    black_box: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pregnancy_category: Mapped[str | None] = mapped_column(String(10))  # A|B|C|D|X|N/A
    paediatric_caution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    renal_caution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
