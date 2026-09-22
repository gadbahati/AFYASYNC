"""Ambulance / emergency transport requests."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AmbulanceRequest(Base):
    __tablename__ = "ambulance_requests"
    __table_args__ = (
        Index("ix_ambulance_status", "status"),
        Index("ix_ambulance_facility_status", "facility_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    person_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("persons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # Receiving / coordinating facility
    requester_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    pickup_location: Mapped[str] = mapped_column(String(300), nullable=False)
    destination: Mapped[str | None] = mapped_column(String(300), nullable=True)
    clinical_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="ROUTINE")
    # CRITICAL | URGENT | ROUTINE
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="REQUESTED")
    # REQUESTED | DISPATCHED | EN_ROUTE | ARRIVED | COMPLETED | CANCELLED | DENIED
    vehicle_ref: Mapped[str | None] = mapped_column(String(80), nullable=True)
    eta_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)
    dispatcher_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    outcome_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    handled_by_staff_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("staff.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
