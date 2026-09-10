import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.models import Integration, IntegrationTransaction


class IntegrationError(ValueError):
    pass


def create_integration(db: Session, facility_id: UUID, name: str, integration_type: str, provider: str, configuration: dict) -> Integration:
    integration = Integration(facility_id=facility_id, name=name, integration_type=integration_type, provider=provider, configuration=configuration, status="ACTIVE")
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def queue_transaction(db: Session, facility_id: UUID, integration_id: UUID, transaction_id: str, entity_type: str, entity_id: UUID | None, direction: str, request_reference: str | None) -> IntegrationTransaction:
    integration = db.scalar(select(Integration).where(Integration.id == integration_id, Integration.facility_id == facility_id))
    if integration is None:
        raise IntegrationError("INTEGRATION_NOT_FOUND")
    if integration.status != "ACTIVE":
        raise IntegrationError("INTEGRATION_NOT_ACTIVE")
    existing = db.scalar(select(IntegrationTransaction).where(IntegrationTransaction.integration_id == integration_id, IntegrationTransaction.transaction_id == transaction_id).limit(1))
    if existing is not None:
        return existing
    transaction = IntegrationTransaction(integration_id=integration_id, transaction_id=transaction_id, entity_type=entity_type, entity_id=entity_id, direction=direction, request_reference=request_reference, status="PENDING", attempt_count=0, response_data={})
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def mark_transaction_result(db: Session, transaction_id: UUID, status: str, response_code: str | None = None, response_data: dict | None = None, external_reference: str | None = None) -> IntegrationTransaction:
    if status not in {"PENDING", "PROCESSING", "SUCCEEDED", "FAILED", "RETRYING"}:
        raise IntegrationError("INVALID_TRANSACTION_STATUS")
    transaction = db.get(IntegrationTransaction, transaction_id)
    if transaction is None:
        raise IntegrationError("TRANSACTION_NOT_FOUND")
    transaction.status = status
    transaction.attempt_count += 1
    transaction.last_attempt_at = datetime.now(timezone.utc)
    transaction.response_code = response_code
    transaction.external_reference = external_reference
    transaction.response_data = response_data or {}
    db.commit()
    db.refresh(transaction)
    return transaction


def verify_callback_signature(
    integration: Integration,
    timestamp: str,
    signature: str,
    payload: dict,
    *,
    tolerance_seconds: int = 300,
) -> None:
    """Verify an HMAC-SHA256 payer callback using the integration callback secret."""
    secret = integration.configuration.get("callback_secret") if integration.configuration else None
    if not isinstance(secret, str) or not secret:
        raise IntegrationError("CALLBACK_SECRET_NOT_CONFIGURED")
    try:
        timestamp_int = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise IntegrationError("INVALID_CALLBACK_TIMESTAMP") from exc
    if abs(int(time.time()) - timestamp_int) > tolerance_seconds:
        raise IntegrationError("CALLBACK_TIMESTAMP_EXPIRED")
    if not signature.startswith("sha256="):
        raise IntegrationError("INVALID_CALLBACK_SIGNATURE")
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    signed = f"{timestamp}.{body}".encode("utf-8")
    expected = "sha256=" + hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise IntegrationError("INVALID_CALLBACK_SIGNATURE")
