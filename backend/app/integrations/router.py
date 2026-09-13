from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.billing.service import BillingError, process_payment_callback
from app.claims.integration_callback import process_claim_payer_callback
from app.claims.service import ClaimsError
from app.database import get_db
from app.integrations.models import Integration
from app.integrations.preauthorization_callback import PreAuthorizationCallbackError, process_preauthorization_callback
from app.integrations.schemas import IntegrationConfigurationUpdate, IntegrationCreate, IntegrationOut, IntegrationStatusUpdate, PayerCallbackCreate, PaymentCallbackCreate, TransactionCreate, TransactionMonitorOut, TransactionOut
from app.integrations.service import IntegrationError, create_integration, list_integration_transactions, list_integrations, queue_transaction, update_integration_configuration, update_integration_status, verify_callback_signature
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])

INTEGRATIONS_WRITE = "integrations.write"
INTEGRATIONS_QUEUE = "integrations.queue"


def _error(exc: IntegrationError | ClaimsError | BillingError | PreAuthorizationCallbackError) -> HTTPException:
    mapping = {
        "INTEGRATION_NOT_FOUND": 404, "TRANSACTION_NOT_FOUND": 404, "INTEGRATION_TRANSACTION_NOT_FOUND": 404,
        "CLAIM_NOT_FOUND": 404, "PAYMENT_NOT_FOUND": 404, "PAYMENT_TRANSACTION_NOT_FOUND": 404,
        "PREAUTH_NOT_FOUND": 404, "PREAUTH_TRANSACTION_NOT_FOUND": 404,
        "INTEGRATION_NOT_ACTIVE": 409, "INVALID_TRANSACTION_STATUS": 400, "INVALID_PAYER_INTEGRATION": 409,
        "PAYER_INTEGRATION_MISMATCH": 409, "PAYER_EXTERNAL_REFERENCE_REQUIRED": 400, "DUPLICATE_PAYER_RESPONSE": 409,
        "INVALID_CLAIM_RESPONSE_STATUS": 400, "CLAIM_RESPONSE_NOT_ALLOWED": 409, "INVALID_APPROVED_AMOUNT": 400,
        "APPROVED_AMOUNT_REQUIRED": 400, "APPROVED_AMOUNT_EXCEEDS_CLAIM": 400, "CLAIM_NOT_READY": 409,
        "INVALID_PAYMENT_INTEGRATION": 409, "PAYMENT_PROVIDER_MISMATCH": 409, "DUPLICATE_PAYMENT_EXTERNAL_REFERENCE": 409,
        "INVALID_PAYMENT_CALLBACK_STATUS": 400, "PAYMENT_ALREADY_FINAL": 409, "PAYMENT_INVALID_STATE": 409,
        "PAYMENT_EXCEEDS_BALANCE": 409, "FACILITY_ACCESS_DENIED": 403, "CALLBACK_SECRET_NOT_CONFIGURED": 503,
        "CALLBACK_SECRET_ENV_NOT_CONFIGURED": 503, "INVALID_CALLBACK_TIMESTAMP": 401, "CALLBACK_TIMESTAMP_EXPIRED": 401, "INVALID_CALLBACK_SIGNATURE": 401,
        "INVALID_PREAUTH_CALLBACK_STATUS": 400, "PREAUTH_EXTERNAL_REFERENCE_REQUIRED": 400, "DUPLICATE_PREAUTH_RESPONSE": 409,
        "PREAUTH_NOT_SUBMITTABLE": 409, "APPROVED_AMOUNT_EXCEEDS_REQUEST": 400, "REJECTED_AMOUNT_MUST_BE_ZERO": 400,
        "PAYER_NOT_ACTIVE": 409, "INVALID_INTEGRATION_CONFIGURATION": 400, "INTEGRATION_SECRET_MUST_USE_ENVIRONMENT": 400,
        "INVALID_INTEGRATION_STATUS": 400, "INTEGRATION_STATUS_UNCHANGED": 409, "INVALID_INTEGRATION_STATUS_TRANSITION": 409,
        "INTEGRATION_STATUS_REASON_REQUIRED": 400, "INTEGRATION_MUST_BE_SUSPENDED": 409, "INTEGRATION_CONFIGURATION_REASON_REQUIRED": 400,
    }
    return HTTPException(status_code=mapping.get(str(exc), 400), detail=str(exc))


@router.get("", response_model=list[IntegrationOut])
def list_all(status: str | None = Query(default=None), db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), _: User = Depends(require_permission(INTEGRATIONS_WRITE))):
    try:
        return list_integrations(db, facility_id, status)
    except IntegrationError as exc: raise _error(exc) from exc


@router.post("", response_model=IntegrationOut, status_code=201)
def create(payload: IntegrationCreate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), _: User = Depends(require_permission(INTEGRATIONS_WRITE))):
    try: return create_integration(db, facility_id, payload.name, payload.integration_type, payload.provider, payload.configuration)
    except IntegrationError as exc: db.rollback(); raise _error(exc) from exc


@router.patch("/{integration_id}/status", response_model=IntegrationOut)
def update_status(integration_id: UUID, payload: IntegrationStatusUpdate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(INTEGRATIONS_WRITE))):
    try: return update_integration_status(db, integration_id, facility_id, payload.status, payload.reason, user.id)
    except IntegrationError as exc: db.rollback(); raise _error(exc) from exc


@router.patch("/{integration_id}/configuration", response_model=IntegrationOut)
def update_configuration(integration_id: UUID, payload: IntegrationConfigurationUpdate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(INTEGRATIONS_WRITE))):
    try:
        return update_integration_configuration(db, integration_id, facility_id, name=payload.name, provider=payload.provider, configuration=payload.configuration, reason=payload.reason, actor_user_id=user.id)
    except IntegrationError as exc:
        db.rollback(); raise _error(exc) from exc


@router.get("/transactions", response_model=list[TransactionMonitorOut])
def transactions(status: str | None = Query(default=None), integration_id: UUID | None = Query(default=None), limit: int = Query(default=100, ge=1, le=500), db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), _: User = Depends(require_permission(INTEGRATIONS_QUEUE))):
    try: return list_integration_transactions(db, facility_id, integration_id=integration_id, status=status, limit=limit)
    except IntegrationError as exc: raise _error(exc) from exc


@router.post("/{integration_id}/transactions", response_model=TransactionOut, status_code=201)
def queue(integration_id: UUID, payload: TransactionCreate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), _: User = Depends(require_permission(INTEGRATIONS_QUEUE))):
    try:
        transaction = queue_transaction(db, facility_id, integration_id, payload.transaction_id, payload.entity_type, payload.entity_id, payload.direction, payload.request_reference)
        db.commit(); db.refresh(transaction); return transaction
    except IntegrationError as exc: db.rollback(); raise _error(exc) from exc


@router.post("/{integration_id}/preauthorizations/{authorization_id}/callback", response_model=dict)
def preauthorization_callback(integration_id: UUID, authorization_id: UUID, payload: PayerCallbackCreate, db: Session = Depends(get_db), x_afasync_timestamp: str = Header(..., alias="X-AfyaSync-Timestamp"), x_afasync_signature: str = Header(..., alias="X-AfyaSync-Signature")):
    try:
        integration = db.get(Integration, integration_id)
        if integration is None: raise IntegrationError("INTEGRATION_NOT_FOUND")
        verify_callback_signature(integration, x_afasync_timestamp, x_afasync_signature, payload.model_dump(mode="json"))
        authorization = process_preauthorization_callback(db, integration_id=integration_id, authorization_id=authorization_id, status=payload.status, response_code=payload.response_code, response_message=payload.response_message, external_reference=payload.external_reference, approved_amount=payload.approved_amount)
        return {"authorization_id": authorization.id, "authorization_number": authorization.authorization_number, "status": authorization.status, "approved_amount": authorization.approved_amount, "external_reference": authorization.external_reference}
    except (IntegrationError, PreAuthorizationCallbackError) as exc: raise _error(exc) from exc


@router.post("/{integration_id}/claims/{claim_id}/callback", response_model=dict)
def payer_callback(integration_id: UUID, claim_id: UUID, payload: PayerCallbackCreate, db: Session = Depends(get_db), x_afasync_timestamp: str = Header(..., alias="X-AfyaSync-Timestamp"), x_afasync_signature: str = Header(..., alias="X-AfyaSync-Signature")):
    try:
        integration = db.get(Integration, integration_id)
        if integration is None: raise IntegrationError("INTEGRATION_NOT_FOUND")
        verify_callback_signature(integration, x_afasync_timestamp, x_afasync_signature, payload.model_dump(mode="json"))
        claim, duplicate = process_claim_payer_callback(db, facility_id=integration.facility_id, integration_id=integration_id, claim_id=claim_id, status=payload.status, response_code=payload.response_code, response_message=payload.response_message, external_reference=payload.external_reference, approved_amount=payload.approved_amount)
        return {"claim_id": claim.id, "claim_number": claim.claim_id, "status": claim.status, "approved_amount": claim.approved_amount, "paid_amount": claim.paid_amount, "duplicate": duplicate}
    except (IntegrationError, ClaimsError) as exc: raise _error(exc) from exc


@router.post("/{integration_id}/payments/{payment_id}/callback", response_model=dict)
def payment_callback(integration_id: UUID, payment_id: UUID, payload: PaymentCallbackCreate, db: Session = Depends(get_db), x_afasync_timestamp: str = Header(..., alias="X-AfyaSync-Timestamp"), x_afasync_signature: str = Header(..., alias="X-AfyaSync-Signature")):
    try:
        integration = db.get(Integration, integration_id)
        if integration is None: raise IntegrationError("INTEGRATION_NOT_FOUND")
        verify_callback_signature(integration, x_afasync_timestamp, x_afasync_signature, payload.model_dump(mode="json"))
        payment = process_payment_callback(db, integration.facility_id, integration_id, payment_id, payload.status, payload.external_reference, payload.response_code, payload.response_message)
        return {"payment_id": payment.id, "transaction_id": payment.transaction_id, "status": payment.status, "external_reference": payment.external_reference}
    except (IntegrationError, BillingError) as exc: raise _error(exc) from exc
