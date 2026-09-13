from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.billing.models import Charge, Service
from app.patients.models import PatientFacility
from app.radiology.models import ImagingOrder, ImagingReport, ImagingTest


def _patient_ok(db: Session, patient_id: UUID, facility_id: UUID) -> bool:
    return db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id == patient_id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE")) is not None


def create_test(db: Session, facility_id: UUID, actor: UUID, payload):
    item = ImagingTest(facility_id=facility_id, **payload.model_dump()); db.add(item)
    record_audit(db, action="IMAGING_TEST_CREATED", resource_type="ImagingTest", result="SUCCESS", user_id=actor, resource_id=str(item.id), facility_id=facility_id, commit=False)
    db.commit(); db.refresh(item); return item


def create_order(db: Session, facility_id: UUID, actor: UUID, payload):
    if not _patient_ok(db, payload.patient_id, facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    test = db.scalar(select(ImagingTest).where(ImagingTest.id == payload.test_id, ImagingTest.facility_id == facility_id, ImagingTest.active.is_(True)))
    if not test: raise ValueError("IMAGING_TEST_NOT_FOUND")
    order = ImagingOrder(order_number=f"IMG-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}", facility_id=facility_id, ordered_by=actor, **payload.model_dump()); db.add(order)
    record_audit(db, action="IMAGING_ORDER_CREATED", resource_type="ImagingOrder", result="SUCCESS", user_id=actor, resource_id=str(order.id), facility_id=facility_id, patient_id=payload.patient_id, commit=False)
    db.commit(); db.refresh(order); return order


def report_order(db: Session, facility_id: UUID, actor: UUID, order_id: UUID, payload):
    order = db.scalar(select(ImagingOrder).where(ImagingOrder.id == order_id, ImagingOrder.facility_id == facility_id).with_for_update())
    if not order: raise ValueError("IMAGING_ORDER_NOT_FOUND")
    if order.status == "COMPLETED": raise ValueError("IMAGING_ALREADY_COMPLETED")
    test = db.scalar(select(ImagingTest).where(ImagingTest.id == order.test_id, ImagingTest.facility_id == facility_id))
    if not test: raise ValueError("IMAGING_TEST_NOT_FOUND")
    report = ImagingReport(order_id=order_id, performed_by=actor, **payload.model_dump()); db.add(report); db.flush()
    service = db.scalar(select(Service).where(Service.facility_id == facility_id, Service.code == f"IMG-{test.code}"))
    if not service:
        service = Service(facility_id=facility_id, code=f"IMG-{test.code}", name=test.name, service_type="RADIOLOGY", price=test.price, status="ACTIVE")
        db.add(service); db.flush()
    charge = Charge(charge_id=f"CHG-{uuid4().hex[:20].upper()}", encounter_id=order.encounter_id, patient_id=order.patient_id, facility_id=facility_id, service_id=service.id, quantity=1, unit_price=test.price, total_amount=test.price, source_type="RADIOLOGY", source_id=report.id)
    db.add(charge); order.status = "COMPLETED"; order.completed_at = datetime.now(timezone.utc)
    record_audit(db, action="IMAGING_REPORT_COMPLETED", resource_type="ImagingReport", result="SUCCESS", user_id=actor, resource_id=str(report.id), facility_id=facility_id, patient_id=order.patient_id, commit=False)
    db.commit(); db.refresh(report); return report
