"""Identity & membership domain models (National Phase 1)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Household(Base):
    __tablename__ = "households"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    head_person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    label: Mapped[str | None] = mapped_column(String(200))
    county: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class HouseholdMember(Base):
    __tablename__ = "household_members"
    __table_args__ = (
        UniqueConstraint("household_id", "person_id", name="uq_household_person"),
        Index("ix_household_members_person", "person_id"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    household_id: Mapped[UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), nullable=False, index=True
    )
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False
    )
    relationship_to_head: Mapped[str] = mapped_column(String(40), nullable=False)
    # HEAD | SPOUSE | CHILD | PARENT | DEPENDANT | OTHER
    is_dependant: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MembershipRecord(Base):
    """Membership / contribution line for a person under a payer context."""

    __tablename__ = "membership_records"
    __table_args__ = (
        Index("ix_membership_person_status", "person_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    payer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("payers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    membership_number: Mapped[str | None] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACTIVE"
    )  # ACTIVE | SUSPENDED | LAPSED | TRANSFERRED | CANCELLED
    scheme_code: Mapped[str | None] = mapped_column(String(80))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    employer_name: Mapped[str | None] = mapped_column(String(200))
    employer_pin: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ContributionEntry(Base):
    __tablename__ = "contribution_entries"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    membership_id: Mapped[UUID] = mapped_column(
        ForeignKey("membership_records.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period_label: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. 2026-09
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    paid_on: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="MANUAL")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RECORDED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdentityCorrection(Base):
    """Controlled correction of identity attributes (not silent overwrite)."""

    __tablename__ = "identity_corrections"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    person_id: Mapped[UUID] = mapped_column(
        ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    old_value_redacted: Mapped[str | None] = mapped_column(String(500))
    new_value_redacted: Mapped[str | None] = mapped_column(String(500))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )  # PENDING | APPROVED | REJECTED
    requested_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IdentityMatchLog(Base):
    """Audit of confidence-engine evaluations (no raw national ID stored)."""

    __tablename__ = "identity_match_logs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("facilities.id", ondelete="SET NULL"), index=True
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)  # CLEAR | MATCHES | BLOCK
    top_score: Mapped[int] = mapped_column(default=0)
    evidence_json: Mapped[dict | None] = mapped_column(JSONB)
    candidate_person_ids: Mapped[list | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
