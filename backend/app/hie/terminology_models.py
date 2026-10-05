"""National terminology registry — canonical codes and local mappings."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TerminologyConcept(Base):
    __tablename__ = "terminology_concepts"
    __table_args__ = (UniqueConstraint("system", "version", "code", name="uq_terminology_system_version_code"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    system: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    code: Mapped[str] = mapped_column(String(200), nullable=False)
    display: Mapped[str] = mapped_column(String(500), nullable=False)
    definition: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="AFYASYNC")
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TerminologyMapping(Base):
    __tablename__ = "terminology_mappings"
    __table_args__ = (
        UniqueConstraint("source_system", "source_code", "target_system", "target_code", name="uq_terminology_mapping"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_system: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    source_code: Mapped[str] = mapped_column(String(200), nullable=False)
    target_system: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    target_code: Mapped[str] = mapped_column(String(200), nullable=False)
    equivalence: Mapped[str] = mapped_column(String(30), nullable=False, default="equivalent")
    source_display: Mapped[str | None] = mapped_column(String(500))
    target_display: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
