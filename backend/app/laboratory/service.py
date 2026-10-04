"""Laboratory domain service — restored Phase 135 + clinical order sync.

Developed by BAHATI GAD WANGWE.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.result_sync import complete_clinical_order_by_link_note, complete_clinical_orders_for_encounter
from app.encounters.models import Encounter
from app.laboratory.models import LabOrder, LabOrderItem, LabResult, LabSample, LabTest
from app.rbac.models import Staff


def _staff(db: Session, staff_id: UUID, facility_id: UUID | None = None) -> Staff:
    staff = db.get(Staff, staff_id)
    if staff is None or staff.status != "ACTIVE":
        raise ValueError("STAFF_NOT_FOUND")
    if facility_id is not None and staff.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")
    return staff


def _encounter(db: Session, encounter_id: UUID) -> Encounter:
    enc = db.get(Encounter, encounter_id)
    if enc is None:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    return enc


def create_test(
    db: Session,
    data: dict,
    *,
    actor_user_id: UUID | None = None,
    facility_id: UUID | None = None,
) -> LabTest:
    code = str(data.get("code") or "").strip().upper()
    if not code:
        raise ValueError("LAB_TEST_CODE_REQUIRED")
    existing = db.scalar(select(LabTest).where(LabTest.code == code))
    if existing:
        raise ValueError("LAB_TEST_CODE_EXISTS")
    test = LabTest(
        code=code,
        name=str(data.get("name") or "").strip(),
        description=data.get("description"),
        category=data.get("category"),
        sample_type=data.get("sample_type"),
        price=float(data.get("price") or 0),
        status="ACTIVE",
    )
    db.add(test)
    db.flush()
    if actor_user_id:
        record_audit(
            db,
            action="LAB_TEST_CREATED",
            resource_type="LAB_TEST",
            resource_id=str(test.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=facility_id,
            metadata={"code": test.code},
            commit=False,
        )
    db.commit()
    db.refresh(test)
    return test


def create_order(db: Session, staff_id: UUID, data: dict, *, actor_user_id: UUID | None = None) -> LabOrder:
    encounter = _encounter(db, data["encounter_id"])
    _staff(db, staff_id, encounter.facility_id)
    items_data = data.get("items") or []
    if not items_data:
        raise ValueError("LAB_ORDER_ITEMS_REQUIRED")
    tests = []
    for item in items_data:
        test = db.get(LabTest, item["test_id"])
        if not test or test.status != "ACTIVE":
            raise ValueError("LAB_TEST_NOT_FOUND")
        tests.append((test, item))
    order = LabOrder(
        order_id=f"LAB-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{str(uuid4())[:6].upper()}",
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        ordered_by=staff_id,
        priority=data.get("priority") or "NORMAL",
        status="ORDERED",
    )
    db.add(order)
    db.flush()
    for _, item in tests:
        db.add(
            LabOrderItem(
                lab_order_id=order.id,
                test_id=item["test_id"],
                instructions=item.get("instructions"),
                status="ORDERED",
            )
        )
    if actor_user_id:
        record_audit(
            db,
            action="LAB_ORDER_CREATED",
            resource_type="LAB_ORDER",
            resource_id=str(order.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=encounter.facility_id,
            patient_id=encounter.patient_id,
            metadata={"order_id": order.order_id},
            commit=False,
        )
    db.commit()
    db.refresh(order)
    return order


def collect_sample(
    db: Session,
    staff_id: UUID,
    lab_order_item_id: UUID,
    *,
    actor_user_id: UUID | None = None,
) -> LabSample:
    item = db.get(LabOrderItem, lab_order_item_id)
    if item is None:
        raise ValueError("LAB_ORDER_ITEM_NOT_FOUND")
    order = db.get(LabOrder, item.lab_order_id)
    if order is None:
        raise ValueError("LAB_ORDER_NOT_FOUND")
    enc = _encounter(db, order.encounter_id)
    _staff(db, staff_id, enc.facility_id)
    sample = LabSample(
        sample_id=f"SMP-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{str(uuid4())[:6].upper()}",
        lab_order_item_id=item.id,
        collected_by=staff_id,
        status="COLLECTED",
    )
    item.status = "SAMPLE_COLLECTED"
    if order.status == "ORDERED":
        order.status = "IN_PROGRESS"
    db.add(sample)
    if actor_user_id:
        record_audit(
            db,
            action="LAB_SAMPLE_COLLECTED",
            resource_type="LAB_SAMPLE",
            resource_id=str(sample.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=enc.facility_id,
            patient_id=order.patient_id,
            commit=False,
        )
    db.commit()
    db.refresh(sample)
    return sample


def receive_sample(
    db: Session,
    staff_id: UUID,
    sample_id: UUID,
    *,
    actor_user_id: UUID | None = None,
) -> LabSample:
    sample = db.get(LabSample, sample_id)
    if sample is None:
        raise ValueError("LAB_SAMPLE_NOT_FOUND")
    item = db.get(LabOrderItem, sample.lab_order_item_id)
    order = db.get(LabOrder, item.lab_order_id) if item else None
    enc = _encounter(db, order.encounter_id) if order else None
    if enc:
        _staff(db, staff_id, enc.facility_id)
    sample.received_at = datetime.now(timezone.utc)
    sample.status = "RECEIVED"
    if item:
        item.status = "SAMPLE_RECEIVED"
    if actor_user_id and enc:
        record_audit(
            db,
            action="LAB_SAMPLE_RECEIVED",
            resource_type="LAB_SAMPLE",
            resource_id=str(sample.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=enc.facility_id,
            patient_id=order.patient_id if order else None,
            commit=False,
        )
    db.commit()
    db.refresh(sample)
    return sample


def enter_result(
    db: Session,
    staff_id: UUID,
    data: dict,
    *,
    actor_user_id: UUID | None = None,
) -> LabResult:
    item = db.get(LabOrderItem, data["lab_order_item_id"])
    if item is None:
        raise ValueError("LAB_ORDER_ITEM_NOT_FOUND")
    sample = db.get(LabSample, data["sample_id"])
    if sample is None or sample.lab_order_item_id != item.id:
        raise ValueError("LAB_SAMPLE_NOT_FOUND")
    order = db.get(LabOrder, item.lab_order_id)
    enc = _encounter(db, order.encounter_id)
    _staff(db, staff_id, enc.facility_id)
    existing = db.scalar(select(LabResult).where(LabResult.lab_order_item_id == item.id))
    if existing:
        raise ValueError("LAB_RESULT_EXISTS")
    result = LabResult(
        lab_order_item_id=item.id,
        sample_id=sample.id,
        result=str(data.get("result") or ""),
        unit=data.get("unit"),
        reference_range=data.get("reference_range"),
        comments=data.get("comments"),
        entered_by=staff_id,
        status="ENTERED",
    )
    item.status = "RESULT_ENTERED"
    db.add(result)
    if actor_user_id:
        record_audit(
            db,
            action="LAB_RESULT_ENTERED",
            resource_type="LAB_RESULT",
            resource_id=str(result.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=enc.facility_id,
            patient_id=order.patient_id,
            commit=False,
        )
    db.commit()
    db.refresh(result)
    return result


def verify_result(
    db: Session,
    staff_id: UUID,
    result_id: UUID,
    *,
    actor_user_id: UUID | None = None,
) -> LabResult:
    result = db.get(LabResult, result_id)
    if result is None:
        raise ValueError("LAB_RESULT_NOT_FOUND")
    if result.status == "VERIFIED":
        raise ValueError("LAB_RESULT_ALREADY_VERIFIED")
    item = db.get(LabOrderItem, result.lab_order_item_id)
    order = db.get(LabOrder, item.lab_order_id) if item else None
    if order is None:
        raise ValueError("LAB_ORDER_NOT_FOUND")
    enc = _encounter(db, order.encounter_id)
    _staff(db, staff_id, enc.facility_id)

    result.verified_by = staff_id
    result.verified_at = datetime.now(timezone.utc)
    result.status = "VERIFIED"
    if item:
        item.status = "RESULT_VERIFIED"

    # Complete lab order when all items verified
    siblings = list(db.scalars(select(LabOrderItem).where(LabOrderItem.lab_order_id == order.id)))
    all_done = True
    for sib in siblings:
        res = db.scalar(select(LabResult).where(LabResult.lab_order_item_id == sib.id))
        if res is None or res.status != "VERIFIED":
            if sib.id != item.id:
                all_done = False
                break
    if all_done:
        order.status = "COMPLETED"

    summary = f"Lab {order.order_id}: {result.result}"
    if result.unit:
        summary += f" {result.unit}"

    # Phase 135 — push result onto clinical orders
    complete_clinical_order_by_link_note(
        db,
        linked_token=str(order.id),
        facility_id=enc.facility_id,
        result_summary=summary,
        actor_user_id=actor_user_id,
    )
    complete_clinical_orders_for_encounter(
        db,
        encounter_id=order.encounter_id,
        facility_id=enc.facility_id,
        order_type="LAB",
        result_summary=summary,
        actor_user_id=actor_user_id,
        patient_id=order.patient_id,
    )

    if actor_user_id:
        record_audit(
            db,
            action="LAB_RESULT_VERIFIED",
            resource_type="LAB_RESULT",
            resource_id=str(result.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=enc.facility_id,
            patient_id=order.patient_id,
            metadata={"order_id": order.order_id, "clinical_sync": True},
            commit=False,
        )
    db.commit()
    db.refresh(result)
    return result


def forward_order_to_prescription(
    db: Session,
    staff_id: UUID,
    order_id: UUID,
    *,
    actor_user_id: UUID | None = None,
) -> LabOrder:
    order = db.get(LabOrder, order_id)
    if order is None:
        raise ValueError("LAB_ORDER_NOT_FOUND")
    enc = _encounter(db, order.encounter_id)
    _staff(db, staff_id, enc.facility_id)
    order.forwarded_at = datetime.now(timezone.utc)
    order.forwarded_by = staff_id
    if order.status != "COMPLETED":
        order.status = "FORWARDED"
    if actor_user_id:
        record_audit(
            db,
            action="LAB_ORDER_FORWARDED",
            resource_type="LAB_ORDER",
            resource_id=str(order.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=enc.facility_id,
            patient_id=order.patient_id,
            commit=False,
        )
    db.commit()
    db.refresh(order)
    return order
