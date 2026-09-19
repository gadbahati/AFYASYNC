"""Patient-initiated appointment requests and two-way facility messaging."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppointmentRequest(Base):
    """Patient asks a facility for an appointment; facility accepts, reschedules, or declines."""

    __tablename__ = "appointment_requests"
    __table_args__ = (
        Index("ix_appt_req_patient", "patient_id"),
        Index("ix_appt_req_facility_status", "facility_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True
    )

    # Patient preference
    preferred_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    patient_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status: PENDING → ACCEPTED | DECLINED | RESCHEDULED | CANCELLED_BY_PATIENT
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING", index=True)

    # Facility response
    facility_response_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    offered_appointment_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    responded_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # If accepted, link to real appointment
    appointment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FacilityMessage(Base):
    """Two-way message between patient and a facility."""

    __tablename__ = "facility_messages"
    __table_args__ = (
        Index("ix_facility_msg_thread", "patient_id", "facility_id", "created_at"),
        Index("ix_facility_msg_facility_unread", "facility_id", "sender_type", "read_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # PATIENT or FACILITY
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    body: Mapped[str] = mapped_column(Text, nullable=False)
    related_request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("appointment_requests.id", ondelete="SET NULL"), nullable=True
    )

    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
