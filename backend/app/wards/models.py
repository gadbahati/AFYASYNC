from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Ward(Base):
    __tablename__ = "wards"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    ward_type: Mapped[str] = mapped_column(String(50), default="GENERAL")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("facility_id", "name", name="uq_ward_facility_name"),)


class Bed(Base):
    __tablename__ = "beds"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    ward_id: Mapped[UUID] = mapped_column(ForeignKey("wards.id", ondelete="RESTRICT"), index=True)
    bed_number: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="AVAILABLE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("ward_id", "bed_number", name="uq_bed_ward_number"),)


class BedAssignment(Base):
    __tablename__ = "bed_assignments"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    bed_id: Mapped[UUID] = mapped_column(ForeignKey("beds.id", ondelete="RESTRICT"), index=True)
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("admissions.id", ondelete="RESTRICT"), index=True)
    assigned_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
