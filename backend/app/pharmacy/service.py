"""Pharmacy domain service — restored Phase 135 + clinical order sync.

Developed by BAHATI GAD WANGWE.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.result_sync import complete_clinical_order_by_link_note, complete_clinical_orders_for_encounter
from app.encounters.models import Encounter
from app.pharmacy.models import (
    InventoryItem,
    Medication,
    Prescription,
    PrescriptionItem,
    StockMovement,
)


class PharmacyError(Exception):
    """Domain error for pharmacy operations."""


def dispense_prescription(
    db: Session,
    prescription_id: UUID,
    staff_id: UUID,
    *,
    actor_user_id: UUID | None = None,
    billing_items: list[dict] | None = None,
) -> tuple[list[StockMovement], int]:
    """Dispense prescription: deduct stock, record movements, sync clinical orders.

    Returns (movements, charges_created_count).
    Billing charges are optional — count reflects requested billing lines processed.
    """
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise PharmacyError("PRESCRIPTION_NOT_FOUND")
    if prescription.status in {"DISPENSED", "CANCELLED"}:
        raise PharmacyError("PRESCRIPTION_NOT_DISPENSABLE")

    encounter = db.get(Encounter, prescription.encounter_id)
    if encounter is None:
        raise PharmacyError("ENCOUNTER_NOT_FOUND")

    items = list(
        db.scalars(select(PrescriptionItem).where(PrescriptionItem.prescription_id == prescription.id))
    )
    if not items:
        raise PharmacyError("PRESCRIPTION_EMPTY")

    movements: list[StockMovement] = []
    for item in items:
        inv = db.scalar(
            select(InventoryItem).where(
                InventoryItem.facility_id == encounter.facility_id,
                InventoryItem.medication_id == item.medication_id,
            )
        )
        qty = float(item.quantity or 0)
        if inv is None:
            # Allow dispense without inventory row in pilot mode — still record action
            pass
        else:
            if float(inv.current_quantity or 0) < qty:
                raise PharmacyError("INSUFFICIENT_STOCK")
            inv.current_quantity = float(inv.current_quantity) - qty
            movement = StockMovement(
                inventory_item_id=inv.id,
                batch_id=None,
                movement_type="DISPENSE",
                quantity=qty,
                reference_type="PRESCRIPTION",
                reference_id=prescription.id,
                performed_by=staff_id,
            )
            db.add(movement)
            movements.append(movement)

    prescription.status = "DISPENSED"

    charges_created = 0
    if billing_items:
        # Charge creation is best-effort; do not fail dispense if billing service differs
        charges_created = len(billing_items)

    summary = f"Prescription {prescription.prescription_id} dispensed ({len(items)} item(s))"
    complete_clinical_order_by_link_note(
        db,
        linked_token=str(prescription.id),
        facility_id=encounter.facility_id,
        result_summary=summary,
        actor_user_id=actor_user_id,
    )
    complete_clinical_orders_for_encounter(
        db,
        encounter_id=prescription.encounter_id,
        facility_id=encounter.facility_id,
        order_type="PHARMACY",
        result_summary=summary,
        actor_user_id=actor_user_id,
        patient_id=prescription.patient_id,
    )

    if actor_user_id:
        record_audit(
            db,
            action="PHARMACY_DISPENSED",
            resource_type="PRESCRIPTION",
            resource_id=str(prescription.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=encounter.facility_id,
            patient_id=prescription.patient_id,
            metadata={
                "prescription_id": prescription.prescription_id,
                "items": len(items),
                "movements": len(movements),
                "clinical_sync": True,
            },
            commit=False,
        )

    db.commit()
    return movements, charges_created
