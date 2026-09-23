"""Residual risk entries for national security governance."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ResidualRisk(Base):
    __tablename__ = "residual_risks"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, default="SECURITY")
    # SECURITY | PRIVACY | OPS | COMPLIANCE | INTEGRATION
    inherent_level: Mapped[str] = mapped_column(String(20), nullable=False, default="HIGH")
    residual_level: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    # LOW | MEDIUM | HIGH | CRITICAL
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    # OPEN | MITIGATED | ACCEPTED | CLOSED
    description: Mapped[str] = mapped_column(Text, nullable=False)
    controls: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    treatment: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # MITIGATE | ACCEPT | TRANSFER | AVOID
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
