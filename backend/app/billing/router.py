from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.billing.models import Invoice, Service
from app.billing.permissions import BILLING_CHARGE_WRITE, BILLING_INVOICE_WRITE, BILLING_PAYMENT_WRITE, BILLING_SERVICE_WRITE
from app.billing.schemas import ChargeCreate, ChargeResponse, InvoiceResponse, PaymentCreate, PaymentResponse, ServiceCreate, ServiceResponse
from app.billing.service import BillingError, create_charge, create_invoice, record_payment
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])


def _error(exc: BillingError) -> HTTPException:
    mapping = {"ENCOUNTER_NOT_FOUND": 404, "SERVICE_NOT_FOUND": 404, "INVOICE_NOT_FOUND": 404, "NO_CHARGES": 409, "INVOICE_ALREADY_PAID": 409, "PAYMENT_EXCEEDS_BALANCE": 409, "INVALID_PAYMENT_AMOUNT": 400, "FACILITY_ACCESS_DENIED": 403}
    return HTTPException(status_code=mapping.get(str(exc), 400), detail=str(exc))


@router.post("/services", response_model=ServiceResponse, status_code=201)
def add_service(payload: ServiceCreate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), _: User = Depends(require_permission(BILLING_SERVICE_WRITE))):
    existing = db.scalar(select(Service).where(Service.facility_id == facility_id, Service.code == payload.code))
    if existing:
        raise HTTPException(status_code=409, detail="SERVICE_CODE_EXISTS")
    service = Service(facility_id=facility_id, **payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.post("/charges", response_model=ChargeResponse, status_code=201)
def add_charge(payload: ChargeCreate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), _: User = Depends(require_permission(BILLING_CHARGE_WRITE))):
    try:
        return create_charge(db, facility_id, payload.model_dump())
    except BillingError as exc:
        raise _error(exc) from exc


@router.post("/encounters/{encounter_id}/invoice", response_model=InvoiceResponse, status_code=201)
def make_invoice(encounter_id: UUID, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), _: User = Depends(require_permission(BILLING_INVOICE_WRITE))):
    try:
        return create_invoice(db, facility_id, encounter_id)
    except BillingError as exc:
        raise _error(exc) from exc


@router.post("/payments", response_model=PaymentResponse, status_code=201)
def pay(payload: PaymentCreate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), _: User = Depends(require_permission(BILLING_PAYMENT_WRITE))):
    try:
        return record_payment(db, facility_id, payload.model_dump())
    except BillingError as exc:
        raise _error(exc) from exc
