from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Charge, Service
from app.encounters.models import Encounter
from app.laboratory.models import LabOrder, LabOrderItem, LabResult, LabSample, LabTest
from app.notifications.events import notify_patient_event
from app.rbac.models import Staff


def _staff(db: Session, staff_id: UUID, facility_id: UUID) -> Staff:
    staff = db.get(Staff, staff_id)
    if not staff or staff.status != "ACTIVE" or staff.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")
    return staff


def _encounter(db: Session, encounter_id: UUID) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if not encounter:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    if encounter.status != "OPEN":
        raise ValueError("ENCOUNTER_CLOSED")
    return encounter


def create_test(db: Session, data: dict, *, actor_user_id: UUID | None = None, facility_id: UUID | None = None) -> LabTest:
    code = data["code"].strip().upper()
    existing = db.scalar(select(LabTest).where(LabTest.code == code))
    if existing:
        raise ValueError("LAB_TEST_CODE_EXISTS")
    test = LabTest(
        code=code,
        name=data["name"].strip(),
        description=data.get("description"),
        category=data.get("category"),
        sample_type=data.get("sample_type"),
        price=Decimal(str(data.get("price", 0))),
        status="ACTIVE",
    )
    db.add(test)
    db.flush()
    if actor_user_id:
        record_audit(db, action="LAB_TEST_CREATED", resource_type="LAB_TEST", resource_id=str(test.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, metadata={"code": test.code, "price": str(test.price)}, commit=False)
    db.commit()
    db.refresh(test)
    return test


def create_order(db: Session, staff_id: UUID, data: dict, *, actor_user_id: UUID | None = None) -> LabOrder:
    encounter = _encounter(db, data["encounter_id"])
    _staff(db, staff_id, encounter.facility_id)
    tests = []
    for item in data["items"]:
        test = db.get(LabTest, item["test_id"])
        if not test or test.status != "ACTIVE":
            raise ValueError("LAB_TEST_NOT_FOUND")
        tests.append((test, item))
    order = LabOrder(
        order_id=f"LAB-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{str(uuid4())[:6].upper()}",
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        ordered_by=staff_id,
        priority=data["priority"],
    )
    db.add(order)
    db.flush()
    for _, item in tests:
        db.add(LabOrderItem(lab_order_id=order.id, test_id=item["test_id"], instructions=item.get("instructions")))
    if actor_user_id:
        record_audit(db, action="LAB_ORDER_CREATED", resource_type="LAB_ORDER", resource_id=str(order.id), result="SUCCESS", user_id=actor_user_id, facility_id=encounter.facility_id, patient_id=encounter.patient_id, metadata={"lab_order_id": order.order_id}, commit=False)
    db.commit()
    db.refresh(order)
    return order


def collect_sample(db: Session, staff_id: UUID, item_id: UUID, *, actor_user_id: UUID | None = None) -> LabSample:
    item = db.get(LabOrderItem, item_id)
    if not item:
        raise ValueError("LAB_ORDER_ITEM_NOT_FOUND")
    order = db.get(LabOrder, item.lab_order_id)
    if not order:
        raise ValueError("LAB_ORDER_NOT_FOUND")
    encounter = _encounter(db, order.encounter_id)
    _staff(db, staff_id, encounter.facility_id)
    if item.status != "ORDERED":
        raise ValueError("INVALID_SAMPLE_STATE")
    sample = LabSample(
        sample_id=f"SMP-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{str(uuid4())[:8].upper()}",
        lab_order_item_id=item.id,
        collected_by=staff_id,
    )
    item.status = "SAMPLE_COLLECTED"
    order.status = "SAMPLE_COLLECTED"
    db.add(sample)
    db.flush()
    if actor_user_id:
        record_audit(db, action="LAB_SAMPLE_COLLECTED", resource_type="LAB_SAMPLE", resource_id=str(sample.id), result="SUCCESS", user_id=actor_user_id, facility_id=encounter.facility_id, patient_id=encounter.patient_id, metadata={"sample_id": sample.sample_id}, commit=False)
    db.commit()
    db.refresh(sample)
    return sample


def receive_sample(db: Session, staff_id: UUID, sample_id: UUID, *, actor_user_id: UUID | None = None) -> LabSample:
    sample = db.get(LabSample, sample_id)
    if not sample:
        raise ValueError("SAMPLE_NOT_FOUND")
    item = db.get(LabOrderItem, sample.lab_order_item_id)
    order = db.get(LabOrder, item.lab_order_id)
    encounter = _encounter(db, order.encounter_id)
    _staff(db, staff_id, encounter.facility_id)
    if sample.status != "COLLECTED":
        raise ValueError("INVALID_SAMPLE_STATE")
    sample.received_at = datetime.now(timezone.utc)
    sample.status = "RECEIVED"
    item.status = "SAMPLE_RECEIVED"
    order.status = "PROCESSING"
    if actor_user_id:
        record_audit(db, action="LAB_SAMPLE_RECEIVED", resource_type="LAB_SAMPLE", resource_id=str(sample.id), result="SUCCESS", user_id=actor_user_id, facility_id=encounter.facility_id, patient_id=encounter.patient_id, metadata={"sample_id": sample.sample_id}, commit=False)
    db.commit()
    db.refresh(sample)
    return sample


def _ensure_lab_service(db: Session, facility_id: UUID, test: LabTest) -> Service:
    code = f"LAB-{test.code}"
    service = db.scalar(select(Service).where(Service.facility_id == facility_id, Service.code == code).limit(1))
    if service:
        if service.status != "ACTIVE":
            service.status = "ACTIVE"
        return service
    service = Service(
        facility_id=facility_id,
        code=code,
        name=test.name,
        service_type="LABORATORY",
        price=test.price,
        status="ACTIVE",
    )
    db.add(service)
    db.flush()
    return service


def _create_lab_charge(db: Session, encounter: Encounter, item: LabOrderItem, test: LabTest, result: LabResult, *, actor_user_id: UUID | None = None) -> Charge:
    if item.charge_id:
        existing = db.get(Charge, item.charge_id)
        if existing:
            return existing
    service = _ensure_lab_service(db, encounter.facility_id, test)
    unit_price = Decimal(str(test.price))
    if unit_price <= 0:
        raise ValueError("LAB_TEST_PRICE_REQUIRED")
    charge = Charge(
        charge_id=f"CHG-{uuid4().hex[:20].upper()}",
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        facility_id=encounter.facility_id,
        service_id=service.id,
        quantity=Decimal("1"),
        unit_price=unit_price,
        total_amount=unit_price,
        source_type="LABORATORY",
        source_id=result.id,
    )
    db.add(charge)
    db.flush()
    item.charge_id = charge.id
    record_audit(db, action="LAB_TEST_BILLED", resource_type="CHARGE", resource_id=str(charge.id), result="SUCCESS", user_id=actor_user_id, facility_id=encounter.facility_id, patient_id=encounter.patient_id, metadata={"test_code": test.code, "lab_result_id": str(result.id), "charge_id": charge.charge_id, "unit_price": str(unit_price)}, commit=False)
    return charge


def enter_result(db: Session, staff_id: UUID, data: dict, *, actor_user_id: UUID | None = None) -> LabResult:
    item = db.get(LabOrderItem, data["lab_order_item_id"])
    sample = db.get(LabSample, data["sample_id"])
    if not item or not sample or sample.lab_order_item_id != item.id:
        raise ValueError("SAMPLE_ORDER_MISMATCH")
    order = db.get(LabOrder, item.lab_order_id)
    encounter = _encounter(db, order.encounter_id)
    _staff(db, staff_id, encounter.facility_id)
    if sample.status != "RECEIVED":
        raise ValueError("SAMPLE_NOT_RECEIVED")
    existing = db.scalar(select(LabResult).where(LabResult.lab_order_item_id == item.id))
    if existing:
        raise ValueError("RESULT_ALREADY_ENTERED")
    result = LabResult(**data, entered_by=staff_id)
    db.add(result)
    sample.status = "PROCESSING"
    item.status = "RESULT_ENTERED"
    db.flush()
    if actor_user_id:
        record_audit(db, action="LAB_RESULT_ENTERED", resource_type="LAB_RESULT", resource_id=str(result.id), result="SUCCESS", user_id=actor_user_id, facility_id=encounter.facility_id, patient_id=encounter.patient_id, metadata={"lab_result_id": str(result.id)}, commit=False)
    db.commit()
    db.refresh(result)
    return result


def verify_result(db: Session, staff_id: UUID, result_id: UUID, *, actor_user_id: UUID | None = None) -> LabResult:
    result = db.get(LabResult, result_id)
    if not result:
        raise ValueError("RESULT_NOT_FOUND")
    item = db.get(LabOrderItem, result.lab_order_item_id)
    order = db.get(LabOrder, item.lab_order_id)
    encounter = _encounter(db, order.encounter_id)
    staff = _staff(db, staff_id, encounter.facility_id)
    if result.status != "ENTERED":
        raise ValueError("INVALID_RESULT_STATE")
    test = db.get(LabTest, item.test_id)
    if not test or test.status != "ACTIVE":
        raise ValueError("LAB_TEST_NOT_FOUND")
    if Decimal(str(test.price)) <= 0:
        raise ValueError("LAB_TEST_PRICE_REQUIRED")
    result.verified_by = staff.id
    result.verified_at = datetime.now(timezone.utc)
    result.status = "VERIFIED"
    item.status = "RESULT_VERIFIED"
    _create_lab_charge(db, encounter, item, test, result, actor_user_id=actor_user_id)
    remaining = db.scalar(select(LabOrderItem).where(LabOrderItem.lab_order_id == order.id, LabOrderItem.status != "RESULT_VERIFIED").limit(1))
    if remaining is None:
        order.status = "COMPLETED"
    notify_patient_event(
        db,
        patient_id=encounter.patient_id,
        facility_id=encounter.facility_id,
        event_type="LAB_RESULT_READY",
        action_url=f"/patient/encounters/{encounter.id}/labs",
        actor_user_id=actor_user_id,
        commit=False,
        metadata={"lab_result_id": str(result.id), "lab_order_id": str(order.id)},
    )
    if actor_user_id:
        record_audit(db, action="LAB_RESULT_VERIFIED", resource_type="LAB_RESULT", resource_id=str(result.id), result="SUCCESS", user_id=actor_user_id, facility_id=encounter.facility_id, patient_id=encounter.patient_id, metadata={"lab_result_id": str(result.id), "lab_order_id": str(order.id), "charge_id": str(item.charge_id)}, commit=False)
    db.commit()
    db.refresh(result)
    return result


def forward_order_to_prescription(db: Session, staff_id: UUID, order_id: UUID, *, actor_user_id: UUID | None = None) -> LabOrder:
    order = db.get(LabOrder, order_id)
    if not order:
        raise ValueError("LAB_ORDER_NOT_FOUND")
    encounter = _encounter(db, order.encounter_id)
    staff = _staff(db, staff_id, encounter.facility_id)
    if order.status != "COMPLETED":
        raise ValueError("LAB_ORDER_NOT_COMPLETED")
    pending = db.scalar(select(LabOrderItem).where(LabOrderItem.lab_order_id == order.id, LabOrderItem.status != "RESULT_VERIFIED").limit(1))
    if pending:
        raise ValueError("LAB_RESULTS_PENDING")
    if order.forwarded_at is not None:
        raise ValueError("LAB_ORDER_ALREADY_FORWARDED")
    order.forwarded_at = datetime.now(timezone.utc)
    order.forwarded_by = staff.id
    record_audit(db, action="LAB_RESULTS_FORWARDED_TO_PRESCRIPTION", resource_type="LAB_ORDER", resource_id=str(order.id), result="SUCCESS", user_id=actor_user_id, facility_id=encounter.facility_id, patient_id=encounter.patient_id, metadata={"lab_order_id": order.order_id, "destination": "PRESCRIPTION_REVIEW"}, commit=False)
    db.commit()
    db.refresh(order)
    return order
