"""Lab intelligence models — reference ranges and critical value alerts."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LabTestReference(Base):
    """Numeric reference and critical (panic) ranges for a lab test."""

    __tablename__ = "lab_test_references"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    test_id: Mapped[UUID] = mapped_column(
        ForeignKey("lab_tests.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    unit: Mapped[str | None] = mapped_column(String(50))
    ref_low: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    ref_high: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    critical_low: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    critical_high: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    tat_target_minutes: Mapped[int | None] = mapped_column()  # expected turnaround
    sex_specific: Mapped[str | None] = mapped_column(String(10))  # M|F|ANY
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LabCriticalAlert(Base):
    """Critical / panic value requiring clinical acknowledgement."""

    __tablename__ = "lab_critical_alerts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    lab_result_id: Mapped[UUID] = mapped_column(
        ForeignKey("lab_results.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    encounter_id: Mapped[UUID] = mapped_column(
        ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    test_code: Mapped[str] = mapped_column(String(50), nullable=False)
    test_name: Mapped[str] = mapped_column(String(200), nullable=False)
    result_value: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50))
    flag: Mapped[str] = mapped_column(String(30), nullable=False)  # CRITICAL_LOW|CRITICAL_HIGH|ABNORMAL_LOW|ABNORMAL_HIGH
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="CRITICAL")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)
    # OPEN | ACKNOWLEDGED | CLOSED
    acknowledged_by: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id", ondelete="SET NULL"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ack_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
