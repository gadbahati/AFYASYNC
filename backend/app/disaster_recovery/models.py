"""DR drill runs and backup verification records."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BackupVerification(Base):
    __tablename__ = "backup_verifications"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="POSTGRES")
    # POSTGRES | OBJECT_STORE | WAL
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RECORDED")
    # RECORDED | VERIFIED | FAILED
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DisasterRecoveryDrill(Base):
    __tablename__ = "dr_drills"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    drill_type: Mapped[str] = mapped_column(String(40), nullable=False, default="TABLETOP")
    # TABLETOP | FAILOVER_SIM | RESTORE_TEST
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PLANNED")
    # PLANNED | IN_PROGRESS | PASSED | FAILED | CANCELLED
    scenario: Mapped[str] = mapped_column(String(500), nullable=False)
    outcome_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    rto_minutes_target: Mapped[int | None] = mapped_column(nullable=True)
    rpo_minutes_target: Mapped[int | None] = mapped_column(nullable=True)
    conducted_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
