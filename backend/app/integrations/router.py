from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.integrations.schemas import IntegrationCreate, IntegrationOut, TransactionCreate, TransactionOut
from app.integrations.service import IntegrationError, create_integration, queue_transaction
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])

INTEGRATIONS_WRITE = "integrations.write"
INTEGRATIONS_QUEUE = "integrations.queue"


def _error(exc: IntegrationError) -> HTTPException:
    mapping = {
        "INTEGRATION_NOT_FOUND": 404,
        "TRANSACTION_NOT_FOUND": 404,
        "INTEGRATION_NOT_ACTIVE": 409,
        "INVALID_TRANSACTION_STATUS": 400,
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
