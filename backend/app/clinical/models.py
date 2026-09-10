from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Consultation(Base):
    __tablename__ = "consultations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    encounter_id: Mapped[UUID] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), unique=True, index=True)
    doctor_id: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    chief_complaint: Mapped[str | None] = mapped_column(Text)
    history: Mapped[str | None] = mapped_column(Text)
    examination: Mapped[str | None] = mapped_column(Text)
    assessment: Mapped[str | None] = mapped_column(Text)
    clinical_notes: Mapped[str | None] = mapped_column(Text)
    treatment_plan: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Vital(Base):
    __tablename__ = "vitals"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    encounter_id: Mapped[UUID] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    systolic_bp: Mapped[int | None] = mapped_column()
    diastolic_bp: Mapped[int | None] = mapped_column()
    pulse: Mapped[int | None] = mapped_column()
    temperature_c: Mapped[float | None] = mapped_column(Numeric(4, 1))
    respiratory_rate: Mapped[int | None] = mapped_column()
    oxygen_saturation: Mapped[float | None] = mapped_column(Numeric(5, 2))
    weight_kg: Mapped[float | None] = mapped_column(Numeric(6, 2))
    height_cm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    bmi: Mapped[float | None] = mapped_column(Numeric(5, 2))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    encounter_id: Mapped[UUID] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    diagnosis_code: Mapped[str | None] = mapped_column(String(50))
    diagnosis_name: Mapped[str] = mapped_column(String(250))
    diagnosis_type: Mapped[str] = mapped_column(String(30), default="PRIMARY")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
