"""HIE models — export logs, trusted nodes, inbound documents."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HieExportLog(Base):
    __tablename__ = "hie_export_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    patient_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    export_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    purpose: Mapped[str | None] = mapped_column(String(200))
    purpose_of_use: Mapped[str | None] = mapped_column(String(40))  # TREATMENT|PAYMENT|PUBLICHEALTH|OPERATIONS
    destination: Mapped[str | None] = mapped_column(String(200))
    destination_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("hie_nodes.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="SUCCESS")
    redacted_sensitive: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HieNode(Base):
    """Trusted exchange partner (facility or HIE gateway)."""

    __tablename__ = "hie_nodes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    node_type: Mapped[str] = mapped_column(String(40), nullable=False, default="FACILITY")
    # FACILITY | HIE_GATEWAY | PAYER | NATIONAL_REGISTRY
    endpoint_url: Mapped[str | None] = mapped_column(String(500))
    facility_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    trust_level: Mapped[str] = mapped_column(String(20), nullable=False, default="STANDARD")
    # STANDARD | HIGH | NATIONAL
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HieInboundDocument(Base):
    """Accepted inbound FHIR document from another node."""

    __tablename__ = "hie_inbound_documents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(
        ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    patient_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("persons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("hie_nodes.id", ondelete="SET NULL"), nullable=True
    )
    source_code: Mapped[str | None] = mapped_column(String(80))
    bundle_id: Mapped[str | None] = mapped_column(String(80), index=True)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, default="UNKNOWN")
    resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACCEPTED")
    # ACCEPTED | REJECTED | PARTIAL
    validation_errors: Mapped[list | None] = mapped_column(JSONB)
    payload_meta: Mapped[dict | None] = mapped_column(JSONB)
    received_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
