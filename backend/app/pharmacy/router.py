from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.admissions.models import Admission
from app.audit.service import record_audit
from app.auth.dependencies import get_token_payload, require_permission
from app.clinical.models import Allergy  # noqa: F401 — used by interoperability / legacy paths
from app.database import get_db
from app.encounters.models import Encounter
from app.encounters.service import close_encounter
from app.pharmacy.models import (
    InventoryBatch,
    InventoryItem,
    Medication,
    Prescription,
    PrescriptionItem,
    StockMovement,
)
from app.pharmacy.permissions import (
    PHARMACY_CREATE_MEDICATION,
    PHARMACY_CREATE_PRESCRIPTION,
    PHARMACY_DISPENSE,
    PHARMACY_RECEIVE_INVENTORY,
)
from app.pharmacy.safety_schemas import SafetyCheckRequest, SafetyCheckResponse
from app.pharmacy.safety_service import assert_can_create_prescription, check_prescription_safety
from app.pharmacy.schemas import (
    DispenseRequest,
    DispenseResponse,
    InventoryReceive,
    InventoryResponse,
    MedicationCreate,
    MedicationResponse,
    PrescriptionCreate,
    PrescriptionResponse,
)
from app.pharmacy.service import PharmacyError, dispense_prescription
from app.rbac.models import Staff, User
from app.wards.service import release_bed

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
    staff = db.scalar(
        select(Staff)
        .where(
            Staff.person_id == user.person_id,
            Staff.facility_id == facility_id,
            Staff.status == "ACTIVE",
        )
        .limit(1)
    )
    if staff is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return staff


def _error(exc: PharmacyError) -> HTTPException:
    mapping = {
        "ENCOUNTER_NOT_FOUND": 404,
        "PRESCRIPTION_NOT_FOUND": 404,
        "MEDICATION_NOT_STOCKED": 409,
        "INSUFFICIENT_STOCK": 409,
        "INSUFFICIENT_BATCH_STOCK": 409,
        "ENCOUNTER_CLOSED": 409,
        "PRESCRIPTION_ALREADY_DISPENSED": 409,
        "PRESCRIPTION_NOT_DISPENSABLE": 409,
        "PRESCRIPTION_EMPTY": 409,
        "DUPLICATE_BILLING_ITEM": 400,
        "BILLING_ITEMS_MUST_MATCH_PRESCRIPTION": 400,
        "BILLING_SERVICE_NOT_FOUND": 404,
        "BILLING_FACILITY_ACCESS_DENIED": 403,
    }
    return HTTPException(status_code=mapping.get(str(exc), 400), detail=str(exc))


@router.get("/medications", response_model=list[MedicationResponse])
def list_medications(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PHARMACY_CREATE_PRESCRIPTION)),
    token: dict = Depends(get_token_payload),
):
    _facility(token)
    _ = user
    return list(db.scalars(select(Medication).where(Medication.status == "ACTIVE").order_by(Medication.name)).all())


@router.get("/inventory", response_model=list[InventoryResponse])
def list_inventory(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PHARMACY_RECEIVE_INVENTORY)),
    token: dict = Depends(get_token_payload),
):
    facility_id = _facility(token)
    _ = user
    return list(
        db.scalars(
            select(InventoryItem)
            .where(InventoryItem.facility_id == facility_id)
            .order_by(InventoryItem.medication_id)
        ).all()
    )


@router.get("/prescriptions", response_model=list[PrescriptionResponse])
def list_prescriptions(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PHARMACY_DISPENSE)),
    token: dict = Depends(get_token_payload),
):
    facility_id = _facility(token)
    _ = user
    stmt = (
        select(Prescription)
        .join(Encounter, Encounter.id == Prescription.encounter_id)
        .where(Encounter.facility_id == facility_id)
    )
    if status_filter:
        stmt = stmt.where(Prescription.status == status_filter.upper())
    return list(db.scalars(stmt.order_by(Prescription.created_at.desc()).limit(limit)).all())


@router.post("/medications", response_model=MedicationResponse, status_code=201)
def create_medication(
    payload: MedicationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PHARMACY_CREATE_MEDICATION)),
    token: dict = Depends(get_token_payload),
) -> Medication:
    facility_id = _facility(token)
    _staff(db, user, facility_id)
    if db.scalar(select(Medication).where(Medication.code == payload.code)):
        raise HTTPException(status_code=409, detail="MEDICATION_CODE_EXISTS")
    medication = Medication(**payload.model_dump())
    db.add(medication)
    db.flush()
    record_audit(
        db,
        action="PHARMACY_MEDICATION_CREATED",
        resource_type="MEDICATION",
        resource_id=str(medication.id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        commit=False,
    )
    db.commit()
    db.refresh(medication)
    return medication


@router.post("/safety-check", response_model=SafetyCheckResponse)
def safety_check(
    payload: SafetyCheckRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PHARMACY_CREATE_PRESCRIPTION)),
    token: dict = Depends(get_token_payload),
) -> SafetyCheckResponse:
    """Dry-run prescribe-time allergy / interaction / duplicate check."""
    facility_id = _facility(token)
    _staff(db, user, facility_id)
    try:
        result = check_prescription_safety(
            db,
            patient_id=payload.patient_id,
            facility_id=facility_id,
            medication_ids=[m.medication_id for m in payload.medications],
            encounter_id=payload.encounter_id,
        )
    except ValueError as exc:
        code = str(exc)
        status_map = {
            "ENCOUNTER_NOT_FOUND": 404,
            "MEDICATION_NOT_FOUND": 404,
            "FACILITY_ACCESS_DENIED": 403,
            "PATIENT_ENCOUNTER_MISMATCH": 400,
        }
        raise HTTPException(status_code=status_map.get(code, 400), detail=code) from exc
    record_audit(
        db,
        action="PHARMACY_SAFETY_CHECK",
        resource_type="PERSON",
        resource_id=str(payload.patient_id),
        result="SUCCESS" if result.can_prescribe else "WARNING",
        user_id=user.id,
        facility_id=facility_id,
        patient_id=payload.patient_id,
        metadata={
            "blocking_count": result.blocking_count,
            "warning_count": result.warning_count,
            "allergy_count": result.allergy_count_checked,
        },
        commit=True,
    )
    return result


@router.post("/prescriptions", response_model=PrescriptionResponse, status_code=201)
def create_prescription(
    payload: PrescriptionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PHARMACY_CREATE_PRESCRIPTION)),
    token: dict = Depends(get_token_payload),
) -> Prescription:
    facility_id = _facility(token)
    staff = _staff(db, user, facility_id)
    encounter = db.get(Encounter, payload.encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    if encounter.status != "OPEN":
        raise HTTPException(status_code=409, detail="ENCOUNTER_CLOSED")

    medication_ids = [item.medication_id for item in payload.items]
    try:
        safety = assert_can_create_prescription(
            db,
            patient_id=encounter.patient_id,
            facility_id=facility_id,
            medication_ids=medication_ids,
            encounter_id=encounter.id,
            allergy_override_reason=payload.allergy_override_reason,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "CRITICAL_ALLERGY_BLOCK":
            record_audit(
                db,
                action="PHARMACY_PRESCRIPTION_BLOCKED_ALLERGY",
                resource_type="ENCOUNTER",
                resource_id=str(encounter.id),
                result="DENIED",
                user_id=user.id,
                facility_id=facility_id,
                patient_id=encounter.patient_id,
                metadata={"reason": code},
                commit=True,
            )
            raise HTTPException(status_code=409, detail="CRITICAL_ALLERGY_BLOCK") from exc
        if code == "SAFETY_OVERRIDE_REQUIRED":
            record_audit(
                db,
                action="PHARMACY_PRESCRIPTION_REQUIRES_ALLERGY_REVIEW",
                resource_type="ENCOUNTER",
                resource_id=str(encounter.id),
                result="DENIED",
                user_id=user.id,
                facility_id=facility_id,
                patient_id=encounter.patient_id,
                metadata={"reason": code},
                commit=True,
            )
            raise HTTPException(status_code=409, detail="SAFETY_OVERRIDE_REQUIRED") from exc
        status_map = {
            "ENCOUNTER_NOT_FOUND": 404,
            "MEDICATION_NOT_FOUND": 404,
            "FACILITY_ACCESS_DENIED": 403,
            "PATIENT_ENCOUNTER_MISMATCH": 400,
        }
        raise HTTPException(status_code=status_map.get(code, 400), detail=code) from exc

    # Validate meds exist (safety already did)
    for mid in medication_ids:
        med = db.get(Medication, mid)
        if med is None or med.status != "ACTIVE":
            raise HTTPException(status_code=404, detail="MEDICATION_NOT_FOUND")

    prescription = Prescription(
        prescription_id=f"RX-{uuid4().hex[:20].upper()}",
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        prescribed_by=staff.id,
    )
    db.add(prescription)
    db.flush()
    for item in payload.items:
        db.add(PrescriptionItem(prescription_id=prescription.id, **item.model_dump()))
    db.flush()

    metadata = {
        "item_count": len(payload.items),
        "safety_blocking": safety.blocking_count,
        "safety_warnings": safety.warning_count,
        "allergy_count_checked": safety.allergy_count_checked,
        "allergy_override": bool(payload.allergy_override_reason),
    }
    if payload.allergy_override_reason:
        metadata["allergy_override_reason"] = payload.allergy_override_reason[:200]
    record_audit(
        db,
        action="PHARMACY_PRESCRIPTION_CREATED",
        resource_type="PRESCRIPTION",
        resource_id=str(prescription.id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        patient_id=encounter.patient_id,
        metadata=metadata,
        commit=False,
    )
    db.commit()
    db.refresh(prescription)
    return prescription


@router.post("/inventory/receive", response_model=InventoryResponse, status_code=201)
def receive_inventory(
    payload: InventoryReceive,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PHARMACY_RECEIVE_INVENTORY)),
    token: dict = Depends(get_token_payload),
) -> InventoryItem:
    facility_id = _facility(token)
    staff = _staff(db, user, facility_id)
    if payload.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    medication = db.get(Medication, payload.medication_id)
    if medication is None or medication.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="MEDICATION_NOT_FOUND")
    if payload.expiry_date < date.today():
        raise HTTPException(status_code=400, detail="EXPIRED_BATCH")
    item = db.scalar(
        select(InventoryItem)
        .where(
            InventoryItem.facility_id == facility_id,
            InventoryItem.medication_id == payload.medication_id,
        )
        .with_for_update()
    )
    if item is None:
        item = InventoryItem(
            facility_id=facility_id,
            medication_id=payload.medication_id,
            current_quantity=0,
            minimum_quantity=0,
        )
        db.add(item)
        db.flush()
    batch = db.scalar(
        select(InventoryBatch)
        .where(
            InventoryBatch.inventory_item_id == item.id,
            InventoryBatch.batch_number == payload.batch_number,
        )
        .with_for_update()
    )
    if batch is None:
        batch = InventoryBatch(
            inventory_item_id=item.id,
            batch_number=payload.batch_number,
            expiry_date=payload.expiry_date,
            quantity=payload.quantity,
            purchase_price=payload.purchase_price,
            selling_price=payload.selling_price,
        )
        db.add(batch)
    else:
        if batch.expiry_date != payload.expiry_date:
            raise HTTPException(status_code=409, detail="BATCH_EXPIRY_MISMATCH")
        batch.quantity += payload.quantity
        batch.purchase_price = payload.purchase_price
        batch.selling_price = payload.selling_price
    item.current_quantity += payload.quantity
    db.flush()
    db.add(
        StockMovement(
            inventory_item_id=item.id,
            batch_id=batch.id,
            movement_type="RECEIVE",
            quantity=payload.quantity,
            reference_type="INVENTORY_RECEIPT",
            performed_by=staff.id,
        )
    )
    db.flush()
    record_audit(
        db,
        action="PHARMACY_INVENTORY_RECEIVED",
        resource_type="INVENTORY_ITEM",
        resource_id=str(item.id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        metadata={"batch_number": payload.batch_number, "quantity": payload.quantity},
        commit=False,
    )
    db.commit()
    db.refresh(item)
    return item


@router.post("/prescriptions/{prescription_id}/dispense", response_model=DispenseResponse)
def dispense(
    prescription_id: UUID,
    payload: DispenseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(PHARMACY_DISPENSE)),
    token: dict = Depends(get_token_payload),
) -> DispenseResponse:
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

    # Re-check safety at dispense (allergies may have been updated)
    items = list(
        db.scalars(
            select(PrescriptionItem).where(PrescriptionItem.prescription_id == prescription.id)
        )
    )
    try:
        safety = check_prescription_safety(
            db,
            patient_id=prescription.patient_id,
            facility_id=facility_id,
            medication_ids=[i.medication_id for i in items],
            encounter_id=encounter.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    critical = [c for c in safety.conflicts if c.severity == "CRITICAL" and c.blocking]
    if critical:
        record_audit(
            db,
            action="PHARMACY_DISPENSE_BLOCKED_ALLERGY",
            resource_type="PRESCRIPTION",
            resource_id=str(prescription.id),
            result="DENIED",
            user_id=user.id,
            facility_id=facility_id,
            patient_id=prescription.patient_id,
            metadata={"blocking_count": safety.blocking_count},
            commit=True,
        )
        raise HTTPException(status_code=409, detail="CRITICAL_ALLERGY_BLOCK")

    try:
        movements, charges_created = dispense_prescription(
            db,
            prescription_id,
            staff.id,
            actor_user_id=user.id,
            billing_items=[item.model_dump() for item in payload.billing_items],
        )
    except PharmacyError as exc:
        raise _error(exc) from exc

    admission = db.scalar(
        select(Admission)
        .where(Admission.encounter_id == encounter.id, Admission.facility_id == facility_id)
        .with_for_update()
    )
    if admission is not None and admission.status == "ADMITTED":
        close_encounter(db, encounter.id, actor_user_id=user.id, commit=False)
        from app.wards.models import BedAssignment

        assignment = db.scalar(
            select(BedAssignment)
            .where(
                BedAssignment.admission_id == admission.id,
                BedAssignment.released_at.is_(None),
            )
            .with_for_update()
        )
        if assignment is not None:
            release_bed(db, facility_id, user.id, assignment.bed_id, commit=False)
        admission.status = "DISCHARGED"
        admission.discharged_at = datetime.now(timezone.utc)
        record_audit(
            db,
            action="PATIENT_RELEASED_AFTER_PHARMACY",
            resource_type="ADMISSION",
            resource_id=str(admission.id),
            result="SUCCESS",
            user_id=user.id,
            facility_id=facility_id,
            patient_id=encounter.patient_id,
            metadata={
                "prescription_id": str(prescription_id),
                "encounter_id": str(encounter.id),
                "bed_released": assignment is not None,
            },
            commit=False,
        )
        db.commit()
    prescription = db.get(Prescription, prescription_id)
    return DispenseResponse(
        prescription_id=prescription.id,
        status=prescription.status,
        movements_created=len(movements),
        charges_created=charges_created,
    )
