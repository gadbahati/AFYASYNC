from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class TheatreProcedure(Base):
    __tablename__ = "theatre_procedures"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")

class TheatreBooking(Base):
    __tablename__ = "theatre_bookings"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    procedure_id: Mapped[UUID] = mapped_column(ForeignKey("theatre_procedures.id", ondelete="RESTRICT"))
    surgeon_id: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    anaesthetist_id: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(30), default="SCHEDULED", index=True)
    indication: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class TheatreRecord(Base):
    __tablename__ = "theatre_records"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(ForeignKey("theatre_bookings.id", ondelete="RESTRICT"), unique=True)
    anaesthesia_type: Mapped[str | None] = mapped_column(String(50))
    preoperative_notes: Mapped[str | None] = mapped_column(Text)
    procedure_notes: Mapped[str] = mapped_column(Text)
    postoperative_notes: Mapped[str | None] = mapped_column(Text)
    complications: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(String(80))
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
