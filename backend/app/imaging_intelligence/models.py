"""Imaging critical findings requiring clinical acknowledgement."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImagingCriticalFinding(Base):
    __tablename__ = "imaging_critical_findings"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    report_id: Mapped[UUID] = mapped_column(
        ForeignKey("imaging_reports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("imaging_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    modality: Mapped[str | None] = mapped_column(String(50))
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="CRITICAL")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)
    acknowledged_by: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id", ondelete="SET NULL"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ack_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImagingTestSafety(Base):
    """Per-test safety flags (contrast, pregnancy, radiation)."""

    __tablename__ = "imaging_test_safety"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    test_id: Mapped[UUID] = mapped_column(
        ForeignKey("imaging_tests.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    requires_contrast: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contrast_type: Mapped[str | None] = mapped_column(String(40))  # IODINE | GADOLINIUM | OTHER
    radiation_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pregnancy_caution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
