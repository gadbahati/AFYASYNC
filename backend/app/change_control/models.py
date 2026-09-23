"""Change requests and release records for national governance."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ChangeRequest(Base):
    __tablename__ = "change_requests"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    change_type: Mapped[str] = mapped_column(String(40), nullable=False, default="STANDARD")
    # STANDARD | EMERGENCY | MAJOR
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    # LOW | MEDIUM | HIGH | CRITICAL
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    # DRAFT | SUBMITTED | APPROVED | REJECTED | IMPLEMENTED | ROLLED_BACK
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReleaseRecord(Base):
    __tablename__ = "release_records"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    environment: Mapped[str] = mapped_column(String(30), nullable=False, default="staging")
    # staging | production
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PLANNED")
    # PLANNED | DEPLOYED | VERIFIED | ROLLED_BACK
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("change_requests.id", ondelete="SET NULL"), nullable=True
    )
    deployed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
