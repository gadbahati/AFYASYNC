from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.claims.service import ClaimsError, process_payer_callback
from app.database import get_db
from app.integrations.schemas import IntegrationCreate, IntegrationOut, PayerCallbackCreate, TransactionCreate, TransactionOut
from app.integrations.service import IntegrationError, create_integration, queue_transaction, verify_callback_signature
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])

INTEGRATIONS_WRITE = "integrations.write"
INTEGRATIONS_QUEUE = "integrations.queue"


def _error(exc: IntegrationError | ClaimsError) -> HTTPException:
    mapping = {
        "INTEGRATION_NOT_FOUND": 404,
        "TRANSACTION_NOT_FOUND": 404,
        "INTEGRATION_TRANSACTION_NOT_FOUND": 404,
        "CLAIM_NOT_FOUND": 404,
        "INTEGRATION_NOT_ACTIVE": 409,
        "INVALID_TRANSACTION_STATUS": 400,
        "INVALID_PAYER_INTEGRATION": 409,
        "PAYER_INTEGRATION_MISMATCH": 409,
        "PAYER_EXTERNAL_REFERENCE_REQUIRED": 400,
        "DUPLICATE_PAYER_RESPONSE": 409,
        "INVALID_CLAIM_RESPONSE_STATUS": 400,
        "CLAIM_RESPONSE_NOT_ALLOWED": 409,
        "INVALID_APPROVED_AMOUNT": 400,
        "APPROVED_AMOUNT_REQUIRED": 400,
        "APPROVED_AMOUNT_EXCEEDS_CLAIM": 400,
        "CLAIM_NOT_READY": 409,
        "FACILITY_ACCESS_DENIED": 403,
        "CALLBACK_SECRET_NOT_CONFIGURED": 503,
        "INVALID_CALLBACK_TIMESTAMP": 401,
        "CALLBACK_TIMESTAMP_EXPIRED": 401,
        "INVALID_CALLBACK_SIGNATURE": 401,
    }
    return HTTPException(status_code=mapping.get(str(exc), 400), detail=str(exc))


@router.post("", response_model=IntegrationOut, status_code=201)
def create(
    payload: IntegrationCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    _: User = Depends(require_permission(INTEGRATIONS_WRITE)),
):
    return create_integration(db, facility_id, payload.name, payload.integration_type, payload.provider, payload.configuration)


@router.post("/{integration_id}/transactions", response_model=TransactionOut, status_code=201)
def queue(
    integration_id: UUID,
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    _: User = Depends(require_permission(INTEGRATIONS_QUEUE)),
):
    try:
        return queue_transaction(db, facility_id, integration_id, payload.transaction_id, payload.entity_type, payload.entity_id, payload.direction, payload.request_reference)
    except IntegrationError as exc:
        raise _error(exc) from exc


@router.post("/{integration_id}/claims/{claim_id}/callback", response_model=dict)
def payer_callback(
    integration_id: UUID,
    claim_id: UUID,
    payload: PayerCallbackCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    x_afasync_timestamp: str = Header(..., alias="X-AfyaSync-Timestamp"),
    x_afasync_signature: str = Header(..., alias="X-AfyaSync-Signature"),
):
    try:
        from app.integrations.models import Integration

        integration = db.get(Integration, integration_id)
        if integration is None or integration.facility_id != facility_id:
            raise IntegrationError("INTEGRATION_NOT_FOUND")
        verify_callback_signature(
            integration,
            x_afasync_timestamp,
            x_afasync_signature,
            payload.model_dump(mode="json"),
        )
        claim = process_payer_callback(
            db,
            facility_id,
            integration_id,
            claim_id,
            payload.status,
            payload.response_code,
            payload.response_message,
            payload.external_reference,
            payload.approved_amount,
            actor_user_id=None,
        )
        return {
            "claim_id": claim.id,
            "claim_number": claim.claim_id,
            "status": claim.status,
            "approved_amount": claim.approved_amount,
            "paid_amount": claim.paid_amount,
        }
    except (IntegrationError, ClaimsError) as exc:
        raise _error(exc) from exc
