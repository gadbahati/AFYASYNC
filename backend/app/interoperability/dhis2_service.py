import os
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Invoice, Payment
from app.claims.models import Claim
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.patients.models import PatientFacility


DEFAULT_DATASET_ID = "AFYASYNC_DATASET"
DATA_ELEMENTS = {
    "encounters": "AFYASYNC_ENCOUNTERS",
    "registered_patients": "AFYASYNC_REGISTERED_PATIENTS",
    "invoices": "AFYASYNC_INVOICES",
    "payments": "AFYASYNC_PAYMENTS",
    "claims": "AFYASYNC_CLAIMS",
}


def _month_window(period: str) -> tuple[datetime, datetime]:
    year, month = int(period[:4]), int(period[4:])
    if month < 1 or month > 12:
        raise ValueError("INVALID_DHIS2_PERIOD")
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


def _env_map(prefix: str, defaults: dict[str, str]) -> dict[str, str]:
    return {key: os.getenv(f"{prefix}_{key.upper()}", value).strip() for key, value in defaults.items()}


def build_dhis2_data_value_set(db: Session, *, period: str, actor_user_id: UUID) -> dict:
    start, end = _month_window(period)
    dataset = os.getenv("DHIS2_DATASET_ID", DEFAULT_DATASET_ID).strip()
    if not dataset or len(dataset) > 100:
        raise ValueError("INVALID_DHIS2_DATASET_ID")
    element_map = _env_map("DHIS2_DATA_ELEMENT", DATA_ELEMENTS)

    facilities = list(db.scalars(select(Facility).where(Facility.status == "ACTIVE").order_by(Facility.facility_id)).all())
    data_values = []
    for facility in facilities:
        encounters = db.scalar(select(func.count(Encounter.id)).where(Encounter.facility_id == facility.id, Encounter.created_at >= start, Encounter.created_at < end)) or 0
        patients = db.scalar(select(func.count(func.distinct(PatientFacility.patient_id))).where(PatientFacility.facility_id == facility.id, PatientFacility.created_at >= start, PatientFacility.created_at < end, PatientFacility.status == "ACTIVE")) or 0
        invoices = db.scalar(select(func.count(Invoice.id)).where(Invoice.facility_id == facility.id, Invoice.created_at >= start, Invoice.created_at < end, Invoice.status != "VOID")) or 0
        payments = db.scalar(select(func.count(Payment.id)).where(Payment.facility_id == facility.id, Payment.created_at >= start, Payment.created_at < end, Payment.status == "CONFIRMED")) or 0
        claims = db.scalar(select(func.count(Claim.id)).join(Invoice, Invoice.id == Claim.invoice_id).where(Invoice.facility_id == facility.id, Claim.updated_at >= start, Claim.updated_at < end)) or 0
        values = {
            "encounters": encounters,
            "registered_patients": patients,
            "invoices": invoices,
            "payments": payments,
            "claims": claims,
        }
        for metric, value in values.items():
            data_values.append({"dataElement": element_map[metric], "period": period, "orgUnit": facility.facility_id, "value": str(int(value))})

    record_audit(db, action="EXPORT_DHIS2_AGGREGATES", resource_type="DHIS2_DATA_VALUE_SET", resource_id=period, result="SUCCESS", user_id=actor_user_id, metadata={"dataset": dataset, "facility_count": len(facilities), "data_value_count": len(data_values)})
    return {
        "dataSet": dataset,
        "completeDate": date.today().isoformat(),
        "period": period,
        "dataValues": data_values,
    }
