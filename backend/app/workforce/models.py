"""Staff professional credentials / licences."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProfessionalCredential(Base):
    """Licence / registration held by a staff member (KMPDC, NCK, PPB, etc.)."""

    __tablename__ = "professional_credentials"
    __table_args__ = (
        UniqueConstraint("staff_id", "council_code", "licence_number", name="uq_credential_staff_council_number"),
        Index("ix_credential_expiry", "expiry_date"),
        Index("ix_credential_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    staff_id: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="CASCADE"), nullable=False, index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True)
    council_code: Mapped[str] = mapped_column(String(40), nullable=False)
    # KMPDC | NCK | PPB | COC | OTHER
    cadre: Mapped[str] = mapped_column(String(80), nullable=False)
    # Doctor | Nurse | Pharmacist | Clinical Officer | ...
    licence_number: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    # ACTIVE | EXPIRED | SUSPENDED | REVOKED | PENDING_VERIFICATION
    issued_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
