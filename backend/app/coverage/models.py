from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Payer(Base):
    __tablename__ = "payers"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    payer_type: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    integration_status: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_CONFIGURED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    plans: Mapped[list["PayerPlan"]] = relationship(back_populates="payer")
    coverages: Mapped[list["Coverage"]] = relationship(back_populates="payer")


class PayerPlan(Base):
    __tablename__ = "payer_plans"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    payer_id: Mapped[UUID] = mapped_column(ForeignKey("payers.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    payer: Mapped[Payer] = relationship(back_populates="plans")
    coverages: Mapped[list["Coverage"]] = relationship(back_populates="payer_plan")


class Coverage(Base):
    __tablename__ = "coverage"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, index=True)
    payer_id: Mapped[UUID] = mapped_column(ForeignKey("payers.id", ondelete="RESTRICT"), nullable=False, index=True)
    payer_plan_id: Mapped[UUID | None] = mapped_column(ForeignKey("payer_plans.id", ondelete="RESTRICT"), index=True)
    membership_number: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="UNVERIFIED")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    payer: Mapped[Payer] = relationship(back_populates="coverages")
    payer_plan: Mapped[PayerPlan | None] = relationship(back_populates="coverages")
