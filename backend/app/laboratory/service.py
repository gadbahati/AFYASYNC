from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

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


def create_order(db: Session, staff_id: UUID, data: dict) -> LabOrder:
    encounter = _encounter(db, data["encounter_id"])
    _staff(db, staff_id, encounter.facility_id)
    tests = []
    for item in data["items"]:
        test = db.get(LabTest, item["test_id"])
        if not test or test.status != "ACTIVE":
            raise ValueError("LAB_TEST_NOT_FOUND")
        tests.append((test, item))
    order = LabOrder(
        order_id=f"LAB-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{str(UUID(int=__import__('uuid').uuid4().int))[:6]}",
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        ordered_by=staff_id,
        priority=data["priority"],
    )
    db.add(order)
    db.flush()
    for _, item in tests:
        db.add(LabOrderItem(lab_order_id=order.id, test_id=item["test_id"], instructions=item.get("instructions")))
    db.commit()
    db.refresh(order)
    return order


def collect_sample(db: Session, staff_id: UUID, item_id: UUID) -> LabSample:
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
        sample_id=f"SMP-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{str(__import__('uuid').uuid4())[:8].upper()}",
        lab_order_item_id=item.id,
        collected_by=staff_id,
    )
    item.status = "SAMPLE_COLLECTED"
    order.status = "SAMPLE_COLLECTED"
    db.add(sample)
    db.commit()
    db.refresh(sample)
    return sample


def receive_sample(db: Session, staff_id: UUID, sample_id: UUID) -> LabSample:
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
    db.commit()
    db.refresh(sample)
    return sample


def enter_result(db: Session, staff_id: UUID, data: dict) -> LabResult:
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
    db.commit()
    db.refresh(result)
    return result


def verify_result(db: Session, staff_id: UUID, result_id: UUID) -> LabResult:
    result = db.get(LabResult, result_id)
    if not result:
        raise ValueError("RESULT_NOT_FOUND")
    item = db.get(LabOrderItem, result.lab_order_item_id)
    order = db.get(LabOrder, item.lab_order_id)
    encounter = _encounter(db, order.encounter_id)
    _staff(db, staff_id, encounter.facility_id)
    if result.status != "ENTERED":
        raise ValueError("INVALID_RESULT_STATE")
    result.verified_by = staff_id
    result.verified_at = datetime.now(timezone.utc)
    result.status = "VERIFIED"
    item.status = "RESULT_VERIFIED"
    remaining = db.scalar(select(LabOrderItem).where(LabOrderItem.lab_order_id == order.id, LabOrderItem.status != "RESULT_VERIFIED").limit(1))
    if remaining is None:
        order.status = "COMPLETED"
    notify_patient_event(
        db,
        patient_id=encounter.patient_id,
        facility_id=encounter.facility_id,
        event_type="LAB_RESULT_READY",
        action_url=f"/patient/encounters/{encounter.id}/labs",
        actor_user_id=None,
        commit=False,
        metadata={"lab_result_id": str(result.id), "lab_order_id": str(order.id)},
    )
    db.commit()
    db.refresh(result)
    return result
