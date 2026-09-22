"""Notifiable disease / public-health event reports."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotifiableEvent(Base):
    __tablename__ = "notifiable_events"
    __table_args__ = (
        Index("ix_notifiable_status", "status"),
        Index("ix_notifiable_condition", "condition_code"),
        Index("ix_notifiable_facility_status", "facility_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    person_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("persons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    condition_code: Mapped[str] = mapped_column(String(40), nullable=False)
    # e.g. MALARIA, CHOLERA, MEASLES, TB, COVID19, AFP, OTHER
    condition_name: Mapped[str] = mapped_column(String(120), nullable=False)
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notification_date: Mapped[date] = mapped_column(Date, nullable=False)
    classification: Mapped[str] = mapped_column(String(30), nullable=False, default="SUSPECTED")
    # SUSPECTED | PROBABLE | CONFIRMED | DISCARDED
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    # OPEN | SUBMITTED | ACKNOWLEDGED | CLOSED
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported_by_staff_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
