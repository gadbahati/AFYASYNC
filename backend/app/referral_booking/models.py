from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ReferralBooking(Base):
    __tablename__ = "referral_bookings"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_reference: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    source_facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    destination_facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    referral_id: Mapped[UUID] = mapped_column(ForeignKey("referrals.id", ondelete="RESTRICT"), unique=True, index=True)
    appointment_id: Mapped[UUID] = mapped_column(ForeignKey("appointments.id", ondelete="RESTRICT"), unique=True, index=True)
    coordination_case_id: Mapped[UUID] = mapped_column(ForeignKey("care_coordination_cases.id", ondelete="RESTRICT"), unique=True, index=True)
    service_code: Mapped[str] = mapped_column(String(80), index=True)
    network_code: Mapped[str] = mapped_column(String(80), index=True)
    appointment_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="BOOKED", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
