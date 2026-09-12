from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Admission(Base):
    __tablename__ = "admissions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    admission_number: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[UUID] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), unique=True, index=True)
    benefit_package_code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    ward: Mapped[str] = mapped_column(String(120), nullable=False)
    bed: Mapped[str] = mapped_column(String(50), nullable=False)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ADMITTED", index=True)
    admitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    discharged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
