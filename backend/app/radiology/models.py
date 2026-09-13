from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ImagingTest(Base):
    __tablename__ = "imaging_tests"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(160))
    modality: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(12,2), default=0)
    active: Mapped[bool] = mapped_column(default=True)

class ImagingOrder(Base):
    __tablename__ = "imaging_orders"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    order_number: Mapped[str] = mapped_column(String(50), unique=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    test_id: Mapped[UUID] = mapped_column(ForeignKey("imaging_tests.id", ondelete="RESTRICT"))
    ordered_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    clinical_indication: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ORDERED", index=True)
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class ImagingReport(Base):
    __tablename__ = "imaging_reports"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("imaging_orders.id", ondelete="RESTRICT"), unique=True)
    performed_by: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    findings: Mapped[str] = mapped_column(Text)
    impression: Mapped[str | None] = mapped_column(Text)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
