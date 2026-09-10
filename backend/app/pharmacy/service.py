from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.encounters.models import Encounter
from app.pharmacy.models import InventoryBatch, InventoryItem, MedicationAction, Prescription, PrescriptionItem, StockMovement


class PharmacyError(ValueError):
    pass


def _open_encounter(db: Session, encounter_id: UUID) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise PharmacyError("ENCOUNTER_NOT_FOUND")
    if encounter.status != "OPEN":
        raise PharmacyError("ENCOUNTER_CLOSED")
    return encounter


def dispense_prescription(db: Session, prescription_id: UUID, staff_id: UUID) -> list[StockMovement]:
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise PharmacyError("PRESCRIPTION_NOT_FOUND")
    if prescription.status == "DISPENSED":
        raise PharmacyError("PRESCRIPTION_ALREADY_DISPENSED")
    if prescription.status != "ACTIVE":
        raise PharmacyError("PRESCRIPTION_NOT_DISPENSABLE")

    encounter = _open_encounter(db, prescription.encounter_id)
    items = list(db.scalars(select(PrescriptionItem).where(PrescriptionItem.prescription_id == prescription.id)))
    if not items:
        raise PharmacyError("PRESCRIPTION_EMPTY")

    movements: list[StockMovement] = []
    try:
        for item in items:
            inventory = db.scalar(select(InventoryItem).where(
                InventoryItem.facility_id == encounter.facility_id,
                InventoryItem.medication_id == item.medication_id,
            ).with_for_update())
            if inventory is None:
                raise PharmacyError("MEDICATION_NOT_STOCKED")
            if inventory.current_quantity < item.quantity:
                raise PharmacyError("INSUFFICIENT_STOCK")

            batches = list(db.scalars(select(InventoryBatch).where(
                InventoryBatch.inventory_item_id == inventory.id,
                InventoryBatch.expiry_date >= date.today(),
                InventoryBatch.quantity > 0,
            ).order_by(InventoryBatch.expiry_date.asc(), InventoryBatch.id.asc()).with_for_update()))

            remaining = item.quantity
            for batch in batches:
                if remaining <= 0:
                    break
                allocated = min(batch.quantity, remaining)
                batch.quantity -= allocated
                remaining -= allocated
                movement = StockMovement(
                    inventory_item_id=inventory.id,
                    batch_id=batch.id,
                    movement_type="DISPENSE",
                    quantity=-allocated,
                    reference_type="PRESCRIPTION",
                    reference_id=prescription.id,
                    performed_by=staff_id,
                )
                db.add(movement)
                db.flush()
                movements.append(movement)

            if remaining > 0:
                raise PharmacyError("INSUFFICIENT_BATCH_STOCK")

            inventory.current_quantity -= item.quantity
            db.add(MedicationAction(
                encounter_id=encounter.id,
                prescription_item_id=item.id,
                medication_id=item.medication_id,
                action_type="DISPENSED",
                quantity=item.quantity,
                performed_by=staff_id,
            ))

        prescription.status = "DISPENSED"
        db.commit()
        return movements
    except Exception:
        db.rollback()
        raise
