"""Per-department appointment capacity rules."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DepartmentCapacity(Base):
    """Daily limits and slot size for fair booking."""

    __tablename__ = "department_capacity"
    __table_args__ = (
        UniqueConstraint("facility_id", "department_id", name="uq_dept_capacity_facility_dept"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[UUID] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    max_appointments_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    slot_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    max_pending_requests: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    open_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=8)  # 0-23 local policy
    close_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=17)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
