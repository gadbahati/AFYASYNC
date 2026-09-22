"""Pharmacy Supply OS — low stock, expiry, pre-dispense check, controlled log."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical_safety.models import MedicationSafetyFlag
from app.pharmacy.models import (
    InventoryBatch,
    InventoryItem,
    Medication,
    Prescription,
    PrescriptionItem,
)
from app.pharmacy_supply.models import ControlledDispenseLog


def stock_health(db: Session, facility_id: UUID) -> dict:
    """Facility pharmacy stock dashboard."""
    items = list(
        db.scalars(
            select(InventoryItem).where(
                InventoryItem.facility_id == facility_id,
                InventoryItem.status == "ACTIVE",
            )
        )
    )
    low: list[dict] = []
    zero: list[dict] = []
    for inv in items:
        med = db.get(Medication, inv.medication_id)
        row = {
            "inventory_id": str(inv.id),
            "medication_id": str(inv.medication_id),
            "medication_name": med.name if med else None,
            "medication_code": med.code if med else None,
            "current_quantity": float(inv.current_quantity),
            "minimum_quantity": float(inv.minimum_quantity),
        }
        if Decimal(str(inv.current_quantity)) <= 0:
            zero.append(row)
        elif Decimal(str(inv.current_quantity)) <= Decimal(str(inv.minimum_quantity or 0)):
            low.append(row)

    today = date.today()
    soon = today + timedelta(days=90)
    expiring: list[dict] = []
    expired: list[dict] = []
    batches = list(
        db.scalars(
            select(InventoryBatch)
            .join(InventoryItem, InventoryItem.id == InventoryBatch.inventory_item_id)
            .where(
                InventoryItem.facility_id == facility_id,
                InventoryBatch.quantity > 0,
            )
            .limit(500)
        )
    )
    for b in batches:
        inv = db.get(InventoryItem, b.inventory_item_id)
        med = db.get(Medication, inv.medication_id) if inv else None
        entry = {
            "batch_id": str(b.id),
            "batch_number": b.batch_number,
            "expiry_date": b.expiry_date.isoformat() if b.expiry_date else None,
            "quantity": float(b.quantity),
            "medication_name": med.name if med else None,
        }
        if b.expiry_date and b.expiry_date < today:
            expired.append(entry)
        elif b.expiry_date and b.expiry_date <= soon:
            expiring.append(entry)

    return {
        "facility_id": str(facility_id),
        "active_skus": len(items),
        "low_stock_count": len(low),
        "zero_stock_count": len(zero),
        "expiring_90d_count": len(expiring),
        "expired_batch_count": len(expired),
        "low_stock": low[:50],
        "zero_stock": zero[:50],
        "expiring_90d": expiring[:50],
        "expired_batches": expired[:50],
        "notes": [
            "Dispense already uses FEFO and skips expired batches",
            "Set minimum_quantity on inventory items for low-stock alerts",
        ],
    }


def pre_dispense_check(db: Session, *, facility_id: UUID, prescription_id: UUID) -> dict:
    """Can this prescription be fully dispensed from current non-expired stock?"""
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise ValueError("PRESCRIPTION_NOT_FOUND")
    if prescription.status != "ACTIVE":
        raise ValueError("PRESCRIPTION_NOT_DISPENSABLE")

    items = list(
        db.scalars(
            select(PrescriptionItem).where(PrescriptionItem.prescription_id == prescription.id)
        )
    )
    lines: list[dict] = []
    can_dispense = True
    for item in items:
        med = db.get(Medication, item.medication_id)
        inv = db.scalar(
            select(InventoryItem).where(
                InventoryItem.facility_id == facility_id,
                InventoryItem.medication_id == item.medication_id,
            )
        )
        needed = Decimal(str(item.quantity))
        available = Decimal("0")
        if inv:
            batches = list(
                db.scalars(
                    select(InventoryBatch).where(
                        InventoryBatch.inventory_item_id == inv.id,
                        InventoryBatch.expiry_date >= date.today(),
                        InventoryBatch.quantity > 0,
                    )
                )
            )
            available = sum((Decimal(str(b.quantity)) for b in batches), Decimal("0"))

        ok = inv is not None and available >= needed
        if not ok:
            can_dispense = False

        controlled = False
        flag = db.scalar(
            select(MedicationSafetyFlag).where(
                MedicationSafetyFlag.medication_id == item.medication_id,
                MedicationSafetyFlag.status == "ACTIVE",
            )
        )
        if flag and flag.high_risk:
            controlled = True

        lines.append(
            {
                "prescription_item_id": str(item.id),
                "medication_id": str(item.medication_id),
                "medication_name": med.name if med else None,
                "quantity_needed": float(needed),
                "quantity_available_non_expired": float(available),
                "sufficient": ok,
                "high_risk_flag": controlled,
            }
        )

    return {
        "prescription_id": str(prescription_id),
        "facility_id": str(facility_id),
        "can_dispense": can_dispense,
        "lines": lines,
    }


def log_controlled_dispense(
    db: Session,
    *,
    facility_id: UUID,
    patient_id: UUID,
    prescription_id: UUID,
    medication_id: UUID,
    quantity: Decimal,
    dispensed_by: UUID,
    witness_staff_id: UUID | None = None,
    schedule_class: str | None = None,
    notes: str | None = None,
    actor_user_id: UUID | None = None,
) -> ControlledDispenseLog:
    row = ControlledDispenseLog(
        facility_id=facility_id,
        patient_id=patient_id,
        prescription_id=prescription_id,
        medication_id=medication_id,
        quantity=quantity,
        dispensed_by=dispensed_by,
        witness_staff_id=witness_staff_id,
        schedule_class=schedule_class,
        notes=notes,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        action="CONTROLLED_DISPENSE_LOG",
        resource_type="CONTROLLED_DISPENSE",
        resource_id=str(row.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={"medication_id": str(medication_id), "qty": str(quantity)},
        commit=False,
    )
    return row


def on_prescription_dispensed(
    db: Session,
    *,
    facility_id: UUID,
    patient_id: UUID,
    prescription: Prescription,
    staff_id: UUID,
    actor_user_id: UUID | None = None,
) -> int:
    """Auto-log high-risk meds from prescription items after successful dispense."""
    items = list(
        db.scalars(
            select(PrescriptionItem).where(PrescriptionItem.prescription_id == prescription.id)
        )
    )
    logged = 0
    for item in items:
        flag = db.scalar(
            select(MedicationSafetyFlag).where(
                MedicationSafetyFlag.medication_id == item.medication_id,
                MedicationSafetyFlag.status == "ACTIVE",
                MedicationSafetyFlag.high_risk.is_(True),
            )
        )
        if flag is None:
            continue
        log_controlled_dispense(
            db,
            facility_id=facility_id,
            patient_id=patient_id,
            prescription_id=prescription.id,
            medication_id=item.medication_id,
            quantity=Decimal(str(item.quantity)),
            dispensed_by=staff_id,
            schedule_class="HIGH_RISK",
            notes="Auto-logged from high_risk medication safety flag",
            actor_user_id=actor_user_id,
        )
        logged += 1
    return logged


def list_controlled_logs(
    db: Session, facility_id: UUID, *, limit: int = 50
) -> list[ControlledDispenseLog]:
    limit = min(max(limit, 1), 200)
    return list(
        db.scalars(
            select(ControlledDispenseLog)
            .where(ControlledDispenseLog.facility_id == facility_id)
            .order_by(ControlledDispenseLog.created_at.desc())
            .limit(limit)
        )
    )
