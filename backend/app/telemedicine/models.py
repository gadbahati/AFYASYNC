"""Telemedicine consult requests and outcomes."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TeleConsultRequest(Base):
    __tablename__ = "tele_consult_requests"
    __table_args__ = (
        Index("ix_tele_consult_status", "status"),
        Index("ix_tele_consult_facility_status", "facility_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), nullable=False, default="ROUTINE")
    # ROUTINE | URGENT
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="REQUESTED")
    # REQUESTED | ACCEPTED | DENIED | COMPLETED | CANCELLED
    preferred_window: Mapped[str | None] = mapped_column(String(120), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    facility_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    clinical_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    handled_by_staff_id: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
