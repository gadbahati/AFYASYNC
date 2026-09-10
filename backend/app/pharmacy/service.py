from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Service
from app.billing.service import BillingError, create_charge
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


def _audit(db: Session, *, action: str, resource_type: str, resource_id: UUID, actor_user_id: UUID | None, facility_id: UUID, patient_id: UUID | None = None, metadata: dict | None = None) -> None:
    if actor_user_id:
        record_audit(db, action=action, resource_type=resource_type, resource_id=str(resource_id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=patient_id, metadata=metadata, commit=False)


def dispense_prescription(
    db: Session,
    prescription_id: UUID,
    staff_id: UUID,
    *,
    actor_user_id: UUID | None = None,
    billing_items: list[dict] | None = None,
) -> tuple[list[StockMovement], int]:
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

    billing_items = billing_items or []
    billing_by_item: dict[UUID, UUID] = {}
    for entry in billing_items:
        item_id = UUID(str(entry["prescription_item_id"]))
        service_id = UUID(str(entry["service_id"]))
        if item_id in billing_by_item:
            raise PharmacyError("DUPLICATE_BILLING_ITEM")
        billing_by_item[item_id] = service_id
    if set(billing_by_item) != {item.id for item in items}:
        raise PharmacyError("BILLING_ITEMS_MUST_MATCH_PRESCRIPTION")

    movements: list[StockMovement] = []
    charges_created = 0
    try:
        for item in items:
            service = db.get(Service, billing_by_item[item.id])
            if service is None or service.status != "ACTIVE":
                raise PharmacyError("BILLING_SERVICE_NOT_FOUND")
            if service.facility_id != encounter.facility_id:
                raise PharmacyError("FACILITY_ACCESS_DENIED")

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

            remaining = Decimal(str(item.quantity))
            for batch in batches:
                if remaining <= 0:
                    break
                allocated = min(Decimal(str(batch.quantity)), remaining)
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

            inventory.current_quantity -= Decimal(str(item.quantity))
            db.add(MedicationAction(
                encounter_id=encounter.id,
                prescription_item_id=item.id,
                medication_id=item.medication_id,
                action_type="DISPENSED",
                quantity=item.quantity,
                performed_by=staff_id,
            ))

            try:
                create_charge(
                    db,
                    encounter.facility_id,
                    {"encounter_id": encounter.id, "service_id": service.id, "quantity": item.quantity, "source_type": "PHARMACY_DISPENSE", "source_id": item.id},
                    actor_user_id=actor_user_id,
                    commit=False,
                )
            except BillingError as exc:
                raise PharmacyError(f"BILLING_{exc}") from exc
            charges_created += 1

        prescription.status = "DISPENSED"
        db.flush()
        _audit(db, action="PHARMACY_PRESCRIPTION_DISPENSED", resource_type="PRESCRIPTION", resource_id=prescription.id, actor_user_id=actor_user_id, facility_id=encounter.facility_id, patient_id=encounter.patient_id, metadata={"movement_count": len(movements), "charge_count": charges_created})
        db.commit()
        return movements, charges_created
    except Exception:
        db.rollback()
        raise
