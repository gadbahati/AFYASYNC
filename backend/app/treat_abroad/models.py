"""Models for SHA Treat Abroad (overseas treatment).

SHA covers a fixed list of procedures that cannot currently be performed in Kenya,
subject to pre-authorisation, a financial cap, and treatment only at contracted
foreign facilities.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApprovedOverseasProcedure(Base):
    """Catalogue of procedures SHA has approved for treatment outside Kenya."""

    __tablename__ = "approved_overseas_procedures"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    justification: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # why it is not available in Kenya
    max_cover_kes: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=500000
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OverseasTreatmentCase(Base):
    """A single patient case referred for SHA-funded treatment abroad."""

    __tablename__ = "overseas_treatment_cases"
    __table_args__ = (
        Index("ix_overseas_case_patient", "patient_id"),
        Index("ix_overseas_case_facility", "facility_id"),
        Index("ix_overseas_case_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    case_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)

    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    encounter_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    procedure_id: Mapped[UUID] = mapped_column(
        ForeignKey("approved_overseas_procedures.id", ondelete="RESTRICT"), nullable=False
    )

    # Clinical justification
    clinical_summary: Mapped[str] = mapped_column(Text, nullable=False)
    local_unavailability_reason: Mapped[str] = mapped_column(Text, nullable=False)
    referring_clinician_id: Mapped[UUID] = mapped_column(
        ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False
    )

    # Status machine
    # DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED / REJECTED →
    # TRAVEL_ARRANGED → TREATMENT_IN_PROGRESS → RETURNED → CLOSED
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT", index=True)

    # SHA pre-authorisation
    sha_preauth_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sha_commitment_letter_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_amount_kes: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    sha_decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha_decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Foreign facility
    foreign_hospital_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    foreign_hospital_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    foreign_hospital_city: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Travel & treatment dates
    planned_departure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_departure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    treatment_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    treatment_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    return_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Follow-up in Kenya
    follow_up_facility_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True
    )
    follow_up_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
