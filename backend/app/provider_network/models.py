from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ProviderNetworkMembership(Base):
    __tablename__ = "provider_network_memberships"
    __table_args__ = (UniqueConstraint("facility_id","network_code",name="uq_provider_network_membership"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    network_code: Mapped[str] = mapped_column(String(80), nullable=False)
    network_name: Mapped[str] = mapped_column(String(200), nullable=False)
    participation_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    credential_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    referral_enabled: Mapped[bool] = mapped_column(default=True)
    claims_enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProviderNetworkService(Base):
    __tablename__ = "provider_network_services"
    __table_args__ = (UniqueConstraint("facility_id","service_code","network_code",name="uq_provider_network_service"), Index("ix_provider_network_service_network","network_code","service_code"))
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    network_code: Mapped[str] = mapped_column(String(80), nullable=False)
    service_code: Mapped[str] = mapped_column(String(80), nullable=False)
    service_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department_code: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    tariff_amount: Mapped[Decimal | None] = mapped_column(Numeric(14,2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    referral_required: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ProviderNetworkContract(Base):
    __tablename__ = "provider_network_contracts"
    __table_args__ = (Index("ix_provider_network_contract_network_status","network_code","status"),)
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True)
    network_code: Mapped[str] = mapped_column(String(80), nullable=False)
    contract_reference: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT", index=True)
    payment_terms_days: Mapped[int] = mapped_column(default=30)
    notes: Mapped[str | None] = mapped_column(Text)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
