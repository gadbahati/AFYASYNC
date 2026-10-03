from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BusinessContinuityPlan(Base):
    __tablename__ = "business_continuity_plans"
    __table_args__ = (
        Index("ix_bcp_org_status", "organization_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    service_tier: Mapped[str] = mapped_column(String(30), default="CRITICAL")
    rto_minutes: Mapped[int] = mapped_column(Integer, default=240)
    rpo_minutes: Mapped[int] = mapped_column(Integer, default=60)
    offline_max_hours: Mapped[int] = mapped_column(Integer, default=24)
    backup_cadence_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    owner_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BusinessContinuityEvent(Base):
    __tablename__ = "business_continuity_events"
    __table_args__ = (
        Index("ix_bcp_event_plan_created", "plan_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    plan_id: Mapped[UUID] = mapped_column(ForeignKey("business_continuity_plans.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    measured_rto_minutes: Mapped[int | None] = mapped_column(Integer)
    measured_rpo_minutes: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
