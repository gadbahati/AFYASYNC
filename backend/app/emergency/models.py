from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmergencyVisit(Base):
    __tablename__ = "emergency_visits"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    visit_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=True, index=True)
    arrival_mode: Mapped[str | None] = mapped_column(String(40), nullable=True)
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    triage_level: Mapped[str] = mapped_column(String(20), nullable=False, default="URGENT", index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="WAITING", index=True)
    disposition: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    arrived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class EmergencyTriage(Base):
    __tablename__ = "emergency_triage"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    visit_id: Mapped[UUID] = mapped_column(ForeignKey("emergency_visits.id", ondelete="CASCADE"), unique=True, index=True)
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"), index=True)
    temperature: Mapped[str | None] = mapped_column(String(20), nullable=True)
    heart_rate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    respiratory_rate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    systolic_bp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    diastolic_bp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    oxygen_saturation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pain_score: Mapped[int | None] = mapped_column(nullable=True)
    consciousness: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
