from datetime import date, datetime
from uuid import UUID, uuid4
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ChildHealthRecord(Base):
    __tablename__ = "child_health_records"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    mother_id: Mapped[UUID | None] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    birth_date: Mapped[date | None] = mapped_column(Date)
    birth_weight: Mapped[str | None] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")

class GrowthObservation(Base):
    __tablename__ = "growth_observations"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    child_id: Mapped[UUID] = mapped_column(ForeignKey("child_health_records.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    age_months: Mapped[int | None] = mapped_column(Integer)
    weight: Mapped[str | None] = mapped_column(String(30))
    height: Mapped[str | None] = mapped_column(String(30))
    head_circumference: Mapped[str | None] = mapped_column(String(30))
    assessment: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))

class Immunisation(Base):
    __tablename__ = "immunisations"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    child_id: Mapped[UUID] = mapped_column(ForeignKey("child_health_records.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    vaccine: Mapped[str] = mapped_column(String(120))
    dose: Mapped[str] = mapped_column(String(40))
    administered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    batch_number: Mapped[str | None] = mapped_column(String(80))
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    notes: Mapped[str | None] = mapped_column(Text)
