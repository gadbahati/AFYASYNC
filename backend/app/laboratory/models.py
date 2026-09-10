from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LabTest(Base):
    __tablename__ = "lab_tests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(100))
    sample_type: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class LabOrder(Base):
    __tablename__ = "lab_orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    encounter_id: Mapped[UUID] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    ordered_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL")
    status: Mapped[str] = mapped_column(String(30), default="ORDERED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LabOrderItem(Base):
    __tablename__ = "lab_order_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    lab_order_id: Mapped[UUID] = mapped_column(ForeignKey("lab_orders.id", ondelete="RESTRICT"), index=True)
    test_id: Mapped[UUID] = mapped_column(ForeignKey("lab_tests.id", ondelete="RESTRICT"))
    instructions: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ORDERED", index=True)


class LabSample(Base):
    __tablename__ = "lab_samples"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sample_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    lab_order_item_id: Mapped[UUID] = mapped_column(ForeignKey("lab_order_items.id", ondelete="RESTRICT"), index=True)
    collected_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="COLLECTED", index=True)


class LabResult(Base):
    __tablename__ = "lab_results"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    lab_order_item_id: Mapped[UUID] = mapped_column(ForeignKey("lab_order_items.id", ondelete="RESTRICT"), unique=True, index=True)
    sample_id: Mapped[UUID] = mapped_column(ForeignKey("lab_samples.id", ondelete="RESTRICT"))
    result: Mapped[str] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(50))
    reference_range: Mapped[str | None] = mapped_column(String(100))
    comments: Mapped[str | None] = mapped_column(Text)
    entered_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    verified_by: Mapped[UUID | None] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(30), default="ENTERED", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
