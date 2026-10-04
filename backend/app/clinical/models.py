from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects import postgresql
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
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False, index=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
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
    # When True, this diagnosis is treated as sensitive and requires explicit
    # patient digital consent before it can be shared across facilities.
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CarePlan(Base):
    __tablename__ = "care_plans"
    __table_args__ = (Index("ix_care_plans_facility_patient_status", "facility_id", "patient_id", "status"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(200))
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    interventions: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Allergy(Base):
    __tablename__ = "allergies"
    __table_args__ = (Index("ix_allergies_facility_patient_status", "facility_id", "patient_id", "status"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    allergen: Mapped[str] = mapped_column(String(200))
    reaction: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="UNKNOWN")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TriageAssessment(Base):
    __tablename__ = "triage_assessments"
    __table_args__ = (
        Index("ix_triage_assessments_encounter_assessed_at", "encounter_id", "assessed_at"),
        Index("ix_triage_assessments_priority_assessed_at", "priority", "assessed_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    encounter_id: Mapped[UUID] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    assessed_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    vital_id: Mapped[UUID | None] = mapped_column(ForeignKey("vitals.id", ondelete="SET NULL"), nullable=True)
    acuity: Mapped[int] = mapped_column(nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    red_flags: Mapped[list] = mapped_column(postgresql.JSONB, nullable=False, default=list)
    disposition: Mapped[str | None] = mapped_column(String(40), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Procedure(Base):
    __tablename__ = "clinical_procedures"
    __table_args__ = (Index("ix_clinical_procedures_encounter_performed_at", "encounter_id", "performed_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    encounter_id: Mapped[UUID] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    procedure_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    procedure_name: Mapped[str] = mapped_column(String(250), nullable=False)
    procedure_type: Mapped[str] = mapped_column(String(40), default="CLINICAL", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED", nullable=False, index=True)
    performed_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"
    __table_args__ = (Index("ix_clinical_notes_encounter_created_at", "encounter_id", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    encounter_id: Mapped[UUID] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    note_type: Mapped[str] = mapped_column(String(40), default="PROGRESS", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False, index=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_by: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
