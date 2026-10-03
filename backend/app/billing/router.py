from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.context.service import resolve_facility_ids
from app.billing.models import Invoice, Service
from app.billing.permissions import (
    BILLING_CHARGE_WRITE,
    BILLING_INVOICE_READ,
    BILLING_INVOICE_WRITE,
    BILLING_PAYMENT_WRITE,
    BILLING_SERVICE_READ,
    BILLING_SERVICE_WRITE,
)
from app.billing.schemas import ChargeResponse, InvoiceResponse, PaymentCreate, PaymentResponse, ServiceCreate, ServiceResponse
from app.billing.service import BillingError, create_invoice, record_payment, reprice_invoice_with_benefit_engine
from app.billing.standalone_charge import StandaloneChargeCreate, create_standalone_charge
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])


def _error(exc: BillingError) -> HTTPException:
    code = str(exc)
    mapping = {
        "ENCOUNTER_NOT_FOUND": 404,
        "SERVICE_NOT_FOUND": 404,
        "INVOICE_NOT_FOUND": 404,
        "COVERAGE_NOT_VERIFIED": 409,
        "COVERAGE_RULE_NOT_CONFIGURED": 409,
        "NO_CHARGES": 409,
        "INVOICE_NOT_REPRICABLE": 409,
        "PAYER_REQUIRED_FOR_REPRICE": 409,
        "FACILITY_ACCESS_DENIED": 403,
    }
    return HTTPException(status_code=mapping.get(code, 400), detail={"code": code, "message": code})


@router.get("/services", response_model=list[ServiceResponse])
def list_services(
    scope: str = Query(default="facility"),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(BILLING_SERVICE_READ)),
):
    facility_ids = resolve_facility_ids(db, user.id, scope, session_facility_id=facility_id)
    if not facility_ids:
        return []
    return list(db.scalars(select(Service).where(Service.facility_id.in_(facility_ids)).order_by(Service.code)).all())


@router.get("/invoices", response_model=list[InvoiceResponse])
def list_invoices(
    limit: int = Query(default=50, ge=1, le=200),
    scope: str = Query(default="facility"),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(BILLING_INVOICE_READ)),
):
    facility_ids = resolve_facility_ids(db, user.id, scope, session_facility_id=facility_id)
    if not facility_ids:
        return []
    return list(
        db.scalars(
            select(Invoice)
            .where(Invoice.facility_id.in_(facility_ids))
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        ).all()
    )


@router.post("/services", response_model=ServiceResponse, status_code=201)
def add_service(
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(BILLING_SERVICE_WRITE)),
):
    row = Service(
        facility_id=facility_id,
        code=payload.code,
        name=payload.name,
        department_id=payload.department_id,
        service_type=payload.service_type,
        price=payload.price,
        status="ACTIVE",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/charges", response_model=ChargeResponse, status_code=201)
def add_charge(
    payload: StandaloneChargeCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(BILLING_CHARGE_WRITE)),
):
    try:
        return create_standalone_charge(db, facility_id, payload, actor_user_id=user.id)
    except BillingError as exc:
        raise _error(exc) from exc


@router.post("/encounters/{encounter_id}/invoice", response_model=InvoiceResponse, status_code=201)
def make_invoice(
    encounter_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(BILLING_INVOICE_WRITE)),
):
    try:
        return create_invoice(db, facility_id, encounter_id, actor_user_id=user.id)
    except BillingError as exc:
        raise _error(exc) from exc


@router.post("/invoices/{invoice_id}/reprice-benefits", response_model=InvoiceResponse)
def reprice_invoice_benefits(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(BILLING_INVOICE_WRITE)),
):
    """Phase 105 — apply Universal Benefits & Tariff Engine amounts to invoice lines."""
    try:
        return reprice_invoice_with_benefit_engine(
            db, facility_id, invoice_id, actor_user_id=user.id
        )
    except BillingError as exc:
        raise _error(exc) from exc


@router.post("/payments", response_model=PaymentResponse, status_code=201)
def pay(
    payload: PaymentCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(BILLING_PAYMENT_WRITE)),
):
    if idempotency_key is not None and not 1 <= len(idempotency_key) <= 100:
        raise HTTPException(status_code=400, detail="INVALID_IDEMPOTENCY_KEY")
    data = payload.model_dump()
    data["idempotency_key"] = idempotency_key
    try:
        return record_payment(db, facility_id, data, actor_user_id=user.id)
    except BillingError as exc:
        raise _error(exc) from exc
