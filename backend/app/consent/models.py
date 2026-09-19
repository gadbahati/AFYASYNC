"""Models for patient-controlled sensitive disease disclosure.

When a clinician records a sensitive diagnosis, the patient must give explicit
digital consent (on-screen signature) before the information can be shared
across facilities. If the patient declines, the diagnosis remains facility-local
and will not appear when the patient is searched at another facility.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SensitiveCategory(Base):
    """Configurable list of condition categories treated as sensitive."""

    __tablename__ = "sensitive_categories"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SensitiveDiseaseConsent(Base):
    """Records the patient's explicit decision about sharing a sensitive diagnosis.

    Rules:
    - consent_given = True  → diagnosis may appear in cross-facility searches
    - consent_given = False → diagnosis is facility-local only and must not be
      returned when the patient is looked up at another facility
    - A digital signature (or equivalent proof) is required and stored for audit
    """

    __tablename__ = "sensitive_disease_consents"
    __table_args__ = (
        Index("ix_sensitive_consent_patient_diagnosis", "patient_id", "diagnosis_id"),
        Index("ix_sensitive_consent_facility", "facility_id"),
        Index("ix_sensitive_consent_share", "consent_given", "patient_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Core links
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    diagnosis_id: Mapped[UUID] = mapped_column(
        ForeignKey("diagnoses.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True
    )
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    encounter_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Consent decision
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # FACILITY_ONLY | CROSS_FACILITY (derived from consent_given but kept explicit)
    share_scope: Mapped[str] = mapped_column(String(30), nullable=False, default="FACILITY_ONLY")

    # Optional link to a sensitive category
    sensitive_category_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sensitive_categories.id", ondelete="SET NULL"), nullable=True
    )

    # Digital signature / proof of consent (base64 image, SVG path, or token)
    signature_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    signature_method: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g. "ON_SCREEN_DRAW", "TYPED_NAME", "BIOMETRIC"

    # Who captured the consent and when
    recorded_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    consented_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Audit helpers
    device_id: Mapped[str | None] = mapped_column(String(150), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
