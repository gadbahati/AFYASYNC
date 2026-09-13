from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class BloodUnit(Base):
    __tablename__ = "blood_units"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    donation_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    blood_group: Mapped[str] = mapped_column(String(5))
    component: Mapped[str] = mapped_column(String(40), default="WHOLE_BLOOD")
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="AVAILABLE", index=True)
    screening_status: Mapped[str] = mapped_column(String(30), default="PENDING")
    storage_location: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

class BloodRequest(Base):
    __tablename__ = "blood_requests"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"))
    blood_group: Mapped[str | None] = mapped_column(String(5))
    component: Mapped[str] = mapped_column(String(40), default="WHOLE_BLOOD")
    units_requested: Mapped[int] = mapped_column(Integer, default=1)
    urgency: Mapped[str] = mapped_column(String(30), default="ROUTINE")
    indication: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="REQUESTED", index=True)
    requested_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Crossmatch(Base):
    __tablename__ = "blood_crossmatches"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("blood_requests.id", ondelete="RESTRICT"), index=True)
    blood_unit_id: Mapped[UUID] = mapped_column(ForeignKey("blood_units.id", ondelete="RESTRICT"), index=True)
    patient_blood_group: Mapped[str] = mapped_column(String(5))
    result: Mapped[str] = mapped_column(String(30))
    performed_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)

class Transfusion(Base):
    __tablename__ = "transfusions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(ForeignKey("blood_requests.id", ondelete="RESTRICT"), index=True)
    blood_unit_id: Mapped[UUID] = mapped_column(ForeignKey("blood_units.id", ondelete="RESTRICT"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="STARTED")
    observations: Mapped[str | None] = mapped_column(Text)
    administered_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))

class TransfusionReaction(Base):
    __tablename__ = "transfusion_reactions"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    transfusion_id: Mapped[UUID] = mapped_column(ForeignKey("transfusions.id", ondelete="RESTRICT"), index=True)
    reaction_type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(30))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    action_taken: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)
    reported_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
