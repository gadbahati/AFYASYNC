from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NursingObservation(Base):
    __tablename__ = "nursing_observations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=True, index=True)
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"), index=True)
    temperature: Mapped[str | None] = mapped_column(String(20))
    heart_rate: Mapped[str | None] = mapped_column(String(20))
    respiratory_rate: Mapped[str | None] = mapped_column(String(20))
    systolic_bp: Mapped[str | None] = mapped_column(String(20))
    diastolic_bp: Mapped[str | None] = mapped_column(String(20))
    oxygen_saturation: Mapped[str | None] = mapped_column(String(20))
    pain_score: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class NursingNote(Base):
    __tablename__ = "nursing_notes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=True, index=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"), index=True)
    shift: Mapped[str | None] = mapped_column(String(30))
    note_type: Mapped[str] = mapped_column(String(40), default="PROGRESS")
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class NursingHandover(Base):
    __tablename__ = "nursing_handovers"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    from_shift: Mapped[str] = mapped_column(String(30))
    to_shift: Mapped[str] = mapped_column(String(30))
    handed_over_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    received_by: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
