"""Phase 132 — clinical orders. Developed by BAHATI GAD WANGWE."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClinicalOrder(Base):
    __tablename__ = "clinical_orders"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    code: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="ROUTINE")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ORDERED", index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    ordered_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
