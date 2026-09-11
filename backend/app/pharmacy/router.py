from datetime import date
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_token_payload, require_permission
from app.database import get_db
from app.encounters.models import Encounter
from app.pharmacy.models import InventoryBatch, InventoryItem, Medication, Prescription, PrescriptionItem, StockMovement
from app.pharmacy.permissions import PHARMACY_CREATE_MEDICATION, PHARMACY_CREATE_PRESCRIPTION, PHARMACY_DISPENSE, PHARMACY_RECEIVE_INVENTORY
from app.pharmacy.schemas import DispenseRequest, DispenseResponse, InventoryReceive, InventoryResponse, MedicationCreate, MedicationResponse, PrescriptionCreate, PrescriptionResponse
from app.pharmacy.service import PharmacyError, dispense_prescription
from app.rbac.models import Staff, User

router = APIRouter(prefix="/api/v1/pharmacy", tags=["Pharmacy"])


def _facility(token: dict) -> UUID:
    raw = token.get("facility_id")
    if not raw:
        raise HTTPException(status_code=403, detail="FACILITY_CONTEXT_REQUIRED")
    try:
        return UUID(raw)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=403, detail="INVALID_FACILITY_CONTEXT") from exc


def _staff(db: Session, user: User, facility_id: UUID) -> Staff:
    staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == facility_id, Staff.status == "ACTIVE").limit(1))
    if staff is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return staff


def _error(exc: PharmacyError) -> HTTPException:
    mapping = {
        "ENCOUNTER_NOT_FOUND": 404, "PRESCRIPTION_NOT_FOUND": 404, "MEDICATION_NOT_STOCKED": 409,
        "INSUFFICIENT_STOCK": 409, "INSUFFICIENT_BATCH_STOCK": 409, "ENCOUNTER_CLOSED": 409,
        "PRESCRIPTION_ALREADY_DISPENSED": 409, "PRESCRIPTION_NOT_DISPENSABLE": 409, "PRESCRIPTION_EMPTY": 409,
        "DUPLICATE_BILLING_ITEM": 400, "BILLING_ITEMS_MUST_MATCH_PRESCRIPTION": 400,
        "BILLING_SERVICE_NOT_FOUND": 404, "BILLING_FACILITY_ACCESS_DENIED": 403,
    }
    return HTTPException(status_code=mapping.get(str(exc), 400), detail=str(exc))


@router.post("/medications", response_model=MedicationResponse, status_code=201)
def create_medication(payload: MedicationCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(PHARMACY_CREATE_MEDICATION)), token: dict = Depends(get_token_payload)) -> Medication:
    facility_id = _facility(token)
    _staff(db, user, facility_id)
    existing = db.scalar(select(Medication).where(Medication.code == payload.code))
    if existing:
        raise HTTPException(status_code=409, detail="MEDICATION_CODE_EXISTS")
    medication = Medication(**payload.model_dump())
    db.add(medication)
    db.flush()
    record_audit(db, action="PHARMACY_MEDICATION_CREATED", resource_type="MEDICATION", resource_id=str(medication.id), result="SUCCESS", user_id=user.id, facility_id=facility_id, commit=False)
    db.commit()
    db.refresh(medication)
    return medication


@router.post("/prescriptions", response_model=PrescriptionResponse, status_code=201)
def create_prescription(payload: PrescriptionCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(PHARMACY_CREATE_PRESCRIPTION)), token: dict = Depends(get_token_payload)) -> Prescription:
    facility_id = _facility(token)
    staff = _staff(db, user, facility_id)
    encounter = db.get(Encounter, payload.encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    if encounter.status != "OPEN":
        raise HTTPException(status_code=409, detail="ENCOUNTER_CLOSED")
    prescription = Prescription(prescription_id=f"RX-{uuid4().hex[:20].upper()}", encounter_id=encounter.id, patient_id=encounter.patient_id, prescribed_by=staff.id)
    db.add(prescription)
    db.flush()
    for item in payload.items:
        medication = db.get(Medication, item.medication_id)
        if medication is None or medication.status != "ACTIVE":
            db.rollback()
            raise HTTPException(status_code=404, detail="MEDICATION_NOT_FOUND")
        db.add(PrescriptionItem(prescription_id=prescription.id, **item.model_dump()))
    db.flush()
    record_audit(db, action="PHARMACY_PRESCRIPTION_CREATED", resource_type="PRESCRIPTION", resource_id=str(prescription.id), result="SUCCESS", user_id=user.id, facility_id=facility_id, patient_id=encounter.patient_id, metadata={"item_count": len(payload.items)}, commit=False)
    db.commit()
    db.refresh(prescription)
    return prescription


@router.post("/inventory/receive", response_model=InventoryResponse, status_code=201)
def receive_inventory(payload: InventoryReceive, db: Session = Depends(get_db), user: User = Depends(require_permission(PHARMACY_RECEIVE_INVENTORY)), token: dict = Depends(get_token_payload)) -> InventoryItem:
    facility_id = _facility(token)
    staff = _staff(db, user, facility_id)
    if payload.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    medication = db.get(Medication, payload.medication_id)
    if medication is None or medication.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="MEDICATION_NOT_FOUND")
    if payload.expiry_date < date.today():
        raise HTTPException(status_code=400, detail="EXPIRED_BATCH")
    item = db.scalar(select(InventoryItem).where(InventoryItem.facility_id == facility_id, InventoryItem.medication_id == payload.medication_id).with_for_update())
    if item is None:
        item = InventoryItem(facility_id=facility_id, medication_id=payload.medication_id, current_quantity=0, minimum_quantity=0)
        db.add(item)
        db.flush()
    batch = db.scalar(select(InventoryBatch).where(InventoryBatch.inventory_item_id == item.id, InventoryBatch.batch_number == payload.batch_number).with_for_update())
    if batch is None:
        batch = InventoryBatch(inventory_item_id=item.id, batch_number=payload.batch_number, expiry_date=payload.expiry_date, quantity=payload.quantity, purchase_price=payload.purchase_price, selling_price=payload.selling_price)
        db.add(batch)
    else:
        if batch.expiry_date != payload.expiry_date:
            raise HTTPException(status_code=409, detail="BATCH_EXPIRY_MISMATCH")
        batch.quantity += payload.quantity
        batch.purchase_price = payload.purchase_price
        batch.selling_price = payload.selling_price
    item.current_quantity += payload.quantity
    db.flush()
    db.add(StockMovement(inventory_item_id=item.id, batch_id=batch.id, movement_type="RECEIVE", quantity=payload.quantity, reference_type="INVENTORY_RECEIPT", performed_by=staff.id))
    db.flush()
    record_audit(db, action="PHARMACY_INVENTORY_RECEIVED", resource_type="INVENTORY_ITEM", resource_id=str(item.id), result="SUCCESS", user_id=user.id, facility_id=facility_id, metadata={"batch_number": payload.batch_number, "quantity": payload.quantity}, commit=False)
    db.commit()
    db.refresh(item)
    return item


@router.post("/prescriptions/{prescription_id}/dispense", response_model=DispenseResponse)
def dispense(prescription_id: UUID, payload: DispenseRequest, db: Session = Depends(get_db), user: User = Depends(require_permission(PHARMACY_DISPENSE)), token: dict = Depends(get_token_payload)) -> DispenseResponse:
    facility_id = _facility(token)
    staff = _staff(db, user, facility_id)
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise HTTPException(status_code=404, detail="PRESCRIPTION_NOT_FOUND")
    encounter = db.get(Encounter, prescription.encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try:
        movements, charges_created = dispense_prescription(
            db, prescription_id, staff.id, actor_user_id=user.id,
            billing_items=[item.model_dump() for item in payload.billing_items],
        )
    except PharmacyError as exc:
        raise _error(exc) from exc
    prescription = db.get(Prescription, prescription_id)
    return DispenseResponse(prescription_id=prescription.id, status=prescription.status, movements_created=len(movements), charges_created=charges_created)
