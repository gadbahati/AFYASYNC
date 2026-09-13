from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.billing.models import Charge
from app.patients.models import PatientFacility
from app.radiology.models import ImagingOrder, ImagingReport, ImagingTest


def _patient_ok(db, patient_id, facility_id):
    return db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id==patient_id, PatientFacility.facility_id==facility_id, PatientFacility.status=="ACTIVE")) is not None

def create_test(db, facility_id, actor, payload):
    item=ImagingTest(facility_id=facility_id, **payload.model_dump()); db.add(item)
    record_audit(db, action="IMAGING_TEST_CREATED", resource_type="ImagingTest", result="SUCCESS", user_id=actor, resource_id=str(item.id), facility_id=facility_id, commit=False)
    db.commit(); db.refresh(item); return item

def create_order(db, facility_id, actor, payload):
    if not _patient_ok(db,payload.patient_id,facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    test=db.scalar(select(ImagingTest).where(ImagingTest.id==payload.test_id, ImagingTest.facility_id==facility_id, ImagingTest.active.is_(True)))
    if not test: raise ValueError("IMAGING_TEST_NOT_FOUND")
    order=ImagingOrder(order_number=f"IMG-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}", facility_id=facility_id, ordered_by=actor, **payload.model_dump()); db.add(order)
    record_audit(db, action="IMAGING_ORDER_CREATED", resource_type="ImagingOrder", result="SUCCESS", user_id=actor, resource_id=str(order.id), facility_id=facility_id, patient_id=payload.patient_id, commit=False)
    db.commit(); db.refresh(order); return order

def report_order(db, facility_id, actor, order_id, payload):
    order=db.scalar(select(ImagingOrder).where(ImagingOrder.id==order_id, ImagingOrder.facility_id==facility_id).with_for_update())
    if not order: raise ValueError("IMAGING_ORDER_NOT_FOUND")
    if order.status == "COMPLETED": raise ValueError("IMAGING_ALREADY_COMPLETED")
    report=ImagingReport(order_id=order_id, performed_by=actor, **payload.model_dump()); db.add(report)
    service_code=f"IMG-{db.scalar(select(ImagingTest.code).where(ImagingTest.id==order.test_id))}"
    # Billing is intentionally linked to the configured imaging test price.
    charge=Charge(encounter_id=order.encounter_id, service_id=None, quantity=1, unit_price=db.scalar(select(ImagingTest.price).where(ImagingTest.id==order.test_id)), total_amount=db.scalar(select(ImagingTest.price).where(ImagingTest.id==order.test_id)), source_type="RADIOLOGY", source_id=report.id)
    # If the billing model requires a service FK, this charge is completed by the billing integration layer.
    db.add(charge); order.status="COMPLETED"; order.completed_at=datetime.now(timezone.utc)
    record_audit(db, action="IMAGING_REPORT_COMPLETED", resource_type="ImagingReport", result="SUCCESS", user_id=actor, resource_id=str(report.id), facility_id=facility_id, patient_id=order.patient_id, commit=False)
    db.commit(); db.refresh(report); return report
