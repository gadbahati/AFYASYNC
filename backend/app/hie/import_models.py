"""Provenance-backed inbound HIE clinical resource imports."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HieImportedResource(Base):
    __tablename__ = "hie_imported_resources"
    __table_args__ = (
        UniqueConstraint(
            "source_node_id",
            "resource_type",
            "remote_resource_id",
            name="uq_hie_imported_resource_remote",
        ),
        Index("ix_hie_imported_resources_patient_effective", "patient_id", "effective_at"),
        Index("ix_hie_imported_resources_inbound", "inbound_document_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    inbound_document_id: Mapped[UUID] = mapped_column(
        ForeignKey("hie_inbound_documents.id", ondelete="RESTRICT"), nullable=False
    )
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("hie_nodes.id", ondelete="RESTRICT"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    remote_resource_id: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="IMPORTED", index=True)
    purpose_of_use: Mapped[str] = mapped_column(String(40), nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(30), nullable=False, default="NORMAL")
    normalized_code: Mapped[str | None] = mapped_column(String(100))
    normalized_text: Mapped[str | None] = mapped_column(Text)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    source_provenance: Mapped[dict | None] = mapped_column(JSONB)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    imported_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
