from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(60), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    configuration: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IntegrationTransaction(Base):
    __tablename__ = "integration_transactions"
    __table_args__ = (
        UniqueConstraint("integration_id", "transaction_id", name="uq_integration_transaction"),
        Index(
            "uq_integration_external_reference",
            "integration_id",
            "external_reference",
            unique=True,
            postgresql_where=text("external_reference IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    integration_id: Mapped[UUID] = mapped_column(ForeignKey("integrations.id", ondelete="RESTRICT"), index=True)
    transaction_id: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(nullable=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    request_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    response_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
