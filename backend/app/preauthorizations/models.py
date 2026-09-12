from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PreAuthorization(Base):
    __tablename__ = "preauthorizations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    authorization_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=True, index=True)
    coverage_id: Mapped[UUID] = mapped_column(ForeignKey("coverage.id", ondelete="RESTRICT"), index=True)
    payer_id: Mapped[UUID] = mapped_column(ForeignKey("payers.id", ondelete="RESTRICT"), index=True)
    benefit_package_code: Mapped[str] = mapped_column(String(80), nullable=False)
    care_setting: Mapped[str] = mapped_column(String(20), nullable=False)
    department: Mapped[str] = mapped_column(String(50), nullable=False)
    requested_services: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING", index=True)
    requested_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    approved_amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    external_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
