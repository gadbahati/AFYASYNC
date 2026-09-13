from datetime import date, datetime
from uuid import UUID, uuid4
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Pregnancy(Base):
    __tablename__ = "pregnancies"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    gravida: Mapped[int | None] = mapped_column(Integer)
    para: Mapped[int | None] = mapped_column(Integer)
    lmp: Mapped[date | None] = mapped_column(Date)
    estimated_due_date: Mapped[date | None] = mapped_column(Date)
    gestational_age_weeks: Mapped[int | None] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(30), default="ROUTINE")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AntenatalVisit(Base):
    __tablename__ = "antenatal_visits"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    pregnancy_id: Mapped[UUID] = mapped_column(ForeignKey("pregnancies.id", ondelete="RESTRICT"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    clinician_id: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    visit_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    gestational_age_weeks: Mapped[int | None] = mapped_column(Integer)
    blood_pressure: Mapped[str | None] = mapped_column(String(30))
    weight: Mapped[str | None] = mapped_column(String(30))
    fetal_heart_rate: Mapped[str | None] = mapped_column(String(30))
    findings: Mapped[str | None] = mapped_column(Text)
    plan: Mapped[str | None] = mapped_column(Text)

class Delivery(Base):
    __tablename__ = "deliveries"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    pregnancy_id: Mapped[UUID] = mapped_column(ForeignKey("pregnancies.id", ondelete="RESTRICT"), index=True)
    mother_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    delivery_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(40))
    outcome: Mapped[str] = mapped_column(String(40))
    newborn_count: Mapped[int] = mapped_column(Integer, default=1)
    complications: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))

class Newborn(Base):
    __tablename__ = "newborns"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    delivery_id: Mapped[UUID] = mapped_column(ForeignKey("deliveries.id", ondelete="RESTRICT"), index=True)
    mother_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    patient_id: Mapped[UUID | None] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    sex: Mapped[str | None] = mapped_column(String(20))
    birth_weight: Mapped[str | None] = mapped_column(String(30))
    apgar_1: Mapped[int | None] = mapped_column(Integer)
    apgar_5: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    notes: Mapped[str | None] = mapped_column(Text)
