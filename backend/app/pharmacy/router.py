from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_permission
from app.auth.models import User
from app.database import get_db
from app.encounters.models import Encounter
from app.facilities.models import Staff
from app.pharmacy.models import InventoryBatch, InventoryItem, Medication, Prescription, PrescriptionItem
from app.pharmacy.permissions import PHARMACY_CREATE_MEDICATION, PHARMACY_CREATE_PRESCRIPTION, PHARMACY_DISPENSE, PHARMACY_RECEIVE_INVENTORY
from app.pharmacy.schemas import DispenseResponse, InventoryReceive, InventoryResponse, MedicationCreate, MedicationResponse, PrescriptionCreate, PrescriptionResponse
from app.pharmacy.service import PharmacyError, dispense_prescription

router = APIRouter(prefix="/api/v1/pharmacy", tags=["Pharmacy"])


def _error(exc: PharmacyError) -> HTTPException:
    mapping = {
        "ENCOUNTER_NOT_FOUND": 404,
        "PRESCRIPTION_NOT_FOUND": 404,
        "MEDICATION_NOT_STOCKED": 409,
        "INSUFFICIENT_STOCK": 409,
        "INSUFFICIENT_BATCH_STOCK": 409,
        "ENCOUNTER_CLOSED": 409,
    }
    return HTTPException(status_code=mapping.get(str(exc), 400), detail=str(exc))


@router.post("/medications", response_model=MedicationResponse, status_code=201)
def create_medication(payload: MedicationCreate, db: Session = Depends(get_db), _: User = Depends(require_permission(PHARMACY_CREATE_MEDICATION))) -> Medication:
    existing = db.scalar(select(Medication).where(Medication.code == payload.code))
    if existing:
        raise HTTPException(status_code=409, detail="MEDICATION_CODE_EXISTS")
    medication = Medication(**payload.model_dump())
    db.add(medication)
    db.commit()
    db.refresh(medication)
    return medication


@router.post("/prescriptions", response_model=PrescriptionResponse, status_code=201)
def create_prescription(payload: PrescriptionCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(PHARMACY_CREATE_PRESCRIPTION))) -> Prescription:
    encounter = db.get(Encounter, payload.encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
    if encounter.status != "OPEN":
        raise HTTPException(status_code=409, detail="ENCOUNTER_CLOSED")
    staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == encounter.facility_id, Staff.status == "ACTIVE"))
    if staff is None:
        raise HTTPException(status_code=403, detail="STAFF_NOT_AT_FACILITY")

    prescription = Prescription(
        prescription_id=f"RX-{uuid4().hex[:20].upper()}",
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        prescribed_by=staff.id,
    )
    db.add(prescription)
    db.flush()
    for item in payload.items:
        medication = db.get(Medication, item.medication_id)
        if medication is None or medication.status != "ACTIVE":
            db.rollback()
            raise HTTPException(status_code=404, detail="MEDICATION_NOT_FOUND")
        db.add(PrescriptionItem(prescription_id=prescription.id, **item.model_dump()))
    db.commit()
    db.refresh(prescription)
    return prescription


@router.post("/inventory/receive", response_model=InventoryResponse, status_code=201)
def receive_inventory(payload: InventoryReceive, db: Session = Depends(get_db), _: User = Depends(require_permission(PHARMACY_RECEIVE_INVENTORY))) -> InventoryItem:
    medication = db.get(Medication, payload.medication_id)
    if medication is None or medication.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="MEDICATION_NOT_FOUND")
    if payload.expiry_date < __import__("datetime").date.today():
        raise HTTPException(status_code=400, detail="EXPIRED_BATCH")
    item = db.scalar(select(InventoryItem).where(InventoryItem.facility_id == payload.facility_id, InventoryItem.medication_id == payload.medication_id).with_for_update())
    if item is None:
        item = InventoryItem(facility_id=payload.facility_id, medication_id=payload.medication_id, current_quantity=0, minimum_quantity=0)
        db.add(item)
        db.flush()
    batch = InventoryBatch(inventory_item_id=item.id, batch_number=payload.batch_number, expiry_date=payload.expiry_date, quantity=payload.quantity, purchase_price=payload.purchase_price, selling_price=payload.selling_price)
    db.add(batch)
    item.current_quantity += payload.quantity
    db.commit()
    db.refresh(item)
    return item


@router.post("/prescriptions/{prescription_id}/dispense", response_model=DispenseResponse)
def dispense(prescription_id: UUID, db: Session = Depends(get_db), user: User = Depends(require_permission(PHARMACY_DISPENSE))) -> DispenseResponse:
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise HTTPException(status_code=404, detail="PRESCRIPTION_NOT_FOUND")
    staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == db.get(Encounter, prescription.encounter_id).facility_id, Staff.status == "ACTIVE"))
    if staff is None:
        raise HTTPException(status_code=403, detail="STAFF_REQUIRED")
    try:
        movements = dispense_prescription(db, prescription_id, staff.id)
    except PharmacyError as exc:
        raise _error(exc) from exc
    prescription = db.get(Prescription, prescription_id)
    return DispenseResponse(prescription_id=prescription.id, status=prescription.status, movements_created=len(movements))
