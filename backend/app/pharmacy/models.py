from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Medication(Base):
    __tablename__ = "medications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    generic_name: Mapped[str | None] = mapped_column(String(200))
    strength: Mapped[str | None] = mapped_column(String(100))
    form: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)


class Prescription(Base):
    __tablename__ = "prescriptions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    prescription_id: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    encounter_id: Mapped[UUID] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    prescribed_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    prescription_id: Mapped[UUID] = mapped_column(ForeignKey("prescriptions.id", ondelete="RESTRICT"), index=True)
    medication_id: Mapped[UUID] = mapped_column(ForeignKey("medications.id", ondelete="RESTRICT"))
    dose: Mapped[str] = mapped_column(String(100))
    frequency: Mapped[str] = mapped_column(String(100))
    duration: Mapped[str] = mapped_column(String(100))
    route: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[float] = mapped_column(Numeric(12, 2))
    instructions: Mapped[str | None] = mapped_column(Text)


class MedicationAction(Base):
    __tablename__ = "medication_actions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    encounter_id: Mapped[UUID] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    prescription_item_id: Mapped[UUID | None] = mapped_column(ForeignKey("prescription_items.id", ondelete="RESTRICT"), nullable=True)
    medication_id: Mapped[UUID] = mapped_column(ForeignKey("medications.id", ondelete="RESTRICT"))
    action_type: Mapped[str] = mapped_column(String(40))
    quantity: Mapped[float] = mapped_column(Numeric(12, 2))
    performed_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (UniqueConstraint("facility_id", "medication_id", name="uq_inventory_facility_medication"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    medication_id: Mapped[UUID] = mapped_column(ForeignKey("medications.id", ondelete="RESTRICT"), index=True)
    current_quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    minimum_quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")


class InventoryBatch(Base):
    __tablename__ = "inventory_batches"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    inventory_item_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"), index=True)
    batch_number: Mapped[str] = mapped_column(String(100))
    expiry_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    purchase_price: Mapped[float] = mapped_column(Numeric(12, 2))
    selling_price: Mapped[float] = mapped_column(Numeric(12, 2))


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    inventory_item_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_items.id", ondelete="RESTRICT"), index=True)
    batch_id: Mapped[UUID | None] = mapped_column(ForeignKey("inventory_batches.id", ondelete="RESTRICT"), nullable=True)
    movement_type: Mapped[str] = mapped_column(String(40))
    quantity: Mapped[float] = mapped_column(Numeric(12, 2))
    reference_type: Mapped[str | None] = mapped_column(String(50))
    reference_id: Mapped[UUID | None] = mapped_column(nullable=True)
    performed_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
