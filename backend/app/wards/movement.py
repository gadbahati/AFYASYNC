from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class PatientMovement(Base):
    __tablename__ = "patient_movements"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    admission_id: Mapped[UUID] = mapped_column(ForeignKey("admissions.id", ondelete="RESTRICT"), index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    from_ward: Mapped[str | None] = mapped_column(String(120))
    from_bed: Mapped[str | None] = mapped_column(String(50))
    to_ward: Mapped[str | None] = mapped_column(String(120))
    to_bed: Mapped[str | None] = mapped_column(String(50))
    reason: Mapped[str | None] = mapped_column(Text)
    moved_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
