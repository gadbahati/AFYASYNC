"""Phase 169: patient-controlled HIE data-sharing consent."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class HieConsent(Base):
    __tablename__ = "hie_consents"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False, index=True)
    recipient_node_id: Mapped[UUID | None] = mapped_column(ForeignKey("hie_nodes.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=False, default="PERMIT")
    purpose: Mapped[str] = mapped_column(String(100), nullable=False, default="HOPERAT")
    scope: Mapped[str] = mapped_column(String(50), nullable=False, default="HIE_SHARE")
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="FACILITY")
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    fhir_resource: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
