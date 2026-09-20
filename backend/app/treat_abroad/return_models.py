"""Return-home clinical package after overseas treatment."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OverseasReturnPackage(Base):
    """Structured handoff when patient returns to Kenya after Treat Abroad."""

    __tablename__ = "overseas_return_packages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("overseas_treatment_cases.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Required clinical handoff
    discharge_summary: Mapped[str] = mapped_column(Text, nullable=False)
    procedures_performed: Mapped[str] = mapped_column(Text, nullable=False)
    medications_on_discharge: Mapped[str] = mapped_column(Text, nullable=False)
    complications: Mapped[str | None] = mapped_column(Text, nullable=True)
    foreign_report_refs: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # letter refs / file ids — not binary blobs

    # Local continuity
    follow_up_plan: Mapped[str] = mapped_column(Text, nullable=False)
    follow_up_facility_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True
    )
    recommended_follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rehab_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rehab_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Package lifecycle: DRAFT → ISSUED (locks case into RETURNED path)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT", index=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
