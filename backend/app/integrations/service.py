import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Invoice, Payment
from app.claims.models import Claim
from app.coverage.models import Payer
from app.integrations.models import Integration, IntegrationTransaction
from app.preauthorizations.models import PreAuthorization


class IntegrationError(ValueError):
    pass


_ALLOWED_INTEGRATION_STATUSES = {"ACTIVE", "SUSPENDED", "INACTIVE"}
_ALLOWED_STATUS_TRANSITIONS = {
    "ACTIVE": {"SUSPENDED", "INACTIVE"},
    "SUSPENDED": {"ACTIVE", "INACTIVE"},
    "INACTIVE": {"ACTIVE"},
}
_SENSITIVE_CONFIG_KEYS = {"secret", "callback_secret", "password", "token", "api_key", "apikey", "private_key", "client_secret"}
_ALLOWED_OUTBOUND_ENTITY_TYPES = {"CLAIM", "PAYMENT", "PREAUTHORIZATION"}


def _validate_configuration(configuration: dict) -> dict:
    if not isinstance(configuration, dict):
        raise IntegrationError("INVALID_INTEGRATION_CONFIGURATION")
    for key in configuration:
        normalized = str(key).strip().lower()
        if normalized in _SENSITIVE_CONFIG_KEYS or normalized.endswith("_secret") or normalized.endswith("_token"):
            raise IntegrationError("INTEGRATION_SECRET_MUST_USE_ENVIRONMENT")
    return dict(configuration)


def create_integration(db: Session, facility_id: UUID, name: str, integration_type: str, provider: str, configuration: dict) -> Integration:
    configuration = _validate_configuration(configuration)
    integration = Integration(facility_id=facility_id, name=name.strip(), integration_type=integration_type.strip().upper(), provider=provider.strip().upper(), configuration=configuration, status="ACTIVE")
    db.add(integration)
    db.commit()
    db.refresh(integration)
    return integration


def list_integrations(db: Session, facility_id: UUID, status: str | None = None) -> list[Integration]:
    stmt = select(Integration).where(Integration.facility_id == facility_id)
    if status:
        normalized = status.strip().upper()
        if normalized not in _ALLOWED_INTEGRATION_STATUSES:
            raise IntegrationError("INVALID_INTEGRATION_STATUS")
        stmt = stmt.where(Integration.status == normalized)
    return list(db.scalars(stmt.order_by(Integration.created_at.desc())))


def update_integration_status(db: Session, integration_id: UUID, facility_id: UUID, status: str, reason: str, actor_user_id: UUID) -> Integration:
    integration = db.scalar(select(Integration).where(Integration.id == integration_id, Integration.facility_id == facility_id).with_for_update())
    if integration is None:
        raise IntegrationError("INTEGRATION_NOT_FOUND")
    target = status.strip().upper()
    if target not in _ALLOWED_INTEGRATION_STATUSES:
        raise IntegrationError("INVALID_INTEGRATION_STATUS")
    if target == integration.status:
        raise IntegrationError("INTEGRATION_STATUS_UNCHANGED")
    if target not in _ALLOWED_STATUS_TRANSITIONS.get(integration.status, set()):
        raise IntegrationError("INVALID_INTEGRATION_STATUS_TRANSITION")
    reason = reason.strip()
    if len(reason) < 3:
        raise IntegrationError("INTEGRATION_STATUS_REASON_REQUIRED")
    previous = integration.status
    integration.status = target
    db.flush()
    record_audit(db, action="UPDATE_INTEGRATION_STATUS", resource_type="INTEGRATION", resource_id=str(integration.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, metadata={"previous_status": previous, "new_status": target, "reason": reason}, commit=False)
    db.commit()
    db.refresh(integration)
    return integration


def update_integration_configuration(db: Session, integration_id: UUID, facility_id: UUID, *, name: str | None, provider: str | None, configuration: dict | None, reason: str, actor_user_id: UUID) -> Integration:
    integration = db.scalar(select(Integration).where(Integration.id == integration_id, Integration.facility_id == facility_id).with_for_update())
    if integration is None:
        raise IntegrationError("INTEGRATION_NOT_FOUND")
    if integration.status != "SUSPENDED":
        raise IntegrationError("INTEGRATION_MUST_BE_SUSPENDED")
    reason = reason.strip()
    if len(reason) < 3:
        raise IntegrationError("INTEGRATION_CONFIGURATION_REASON_REQUIRED")
    if name is not None:
        integration.name = name.strip()
    if provider is not None:
        integration.provider = provider.strip().upper()
    if configuration is not None:
        integration.configuration = _validate_configuration(configuration)
    db.flush()
    record_audit(db, action="UPDATE_INTEGRATION_CONFIGURATION", resource_type="INTEGRATION", resource_id=str(integration.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, metadata={"reason": reason, "provider": integration.provider, "configuration_keys": sorted(integration.configuration.keys())}, commit=False)
    db.commit()
    db.refresh(integration)
    return integration


def _validate_outbound_entity(db: Session, facility_id: UUID, entity_type: str, entity_id: UUID) -> None:
    if entity_type == "CLAIM":
        exists = db.scalar(select(Claim.id).join(Invoice, Invoice.id == Claim.invoice_id).where(Claim.id == entity_id, Invoice.facility_id == facility_id))
    elif entity_type == "PAYMENT":
        exists = db.scalar(select(Payment.id).where(Payment.id == entity_id, Payment.facility_id == facility_id))
    elif entity_type == "PREAUTHORIZATION":
        exists = db.scalar(select(PreAuthorization.id).where(PreAuthorization.id == entity_id, PreAuthorization.facility_id == facility_id))
    else:
        raise IntegrationError("UNSUPPORTED_OUTBOUND_ENTITY")
    if exists is None:
        raise IntegrationError("ENTITY_NOT_FOUND_OR_FACILITY_MISMATCH")


def queue_transaction(db: Session, facility_id: UUID, integration_id: UUID, transaction_id: str, entity_type: str, entity_id: UUID | None, direction: str, request_reference: str | None, *, commit: bool = False) -> IntegrationTransaction:
    integration = db.scalar(select(Integration).where(Integration.id == integration_id, Integration.facility_id == facility_id).with_for_update())
    if integration is None:
        raise IntegrationError("INTEGRATION_NOT_FOUND")
    if integration.status != "ACTIVE":
        raise IntegrationError("INTEGRATION_NOT_ACTIVE")
    normalized_transaction_id = transaction_id.strip()
    if not normalized_transaction_id:
        raise IntegrationError("TRANSACTION_ID_REQUIRED")
    normalized_entity_type = entity_type.strip().upper()
    if direction.strip().upper() != "OUTBOUND":
        raise IntegrationError("OUTBOUND_TRANSACTION_REQUIRED")
    if normalized_entity_type not in _ALLOWED_OUTBOUND_ENTITY_TYPES or entity_id is None:
        raise IntegrationError("UNSUPPORTED_OUTBOUND_ENTITY")
    _validate_outbound_entity(db, facility_id, normalized_entity_type, entity_id)
    existing = db.scalar(select(IntegrationTransaction).where(IntegrationTransaction.integration_id == integration_id, IntegrationTransaction.transaction_id == normalized_transaction_id).limit(1))
    if existing is not None:
        return existing
    transaction = IntegrationTransaction(integration_id=integration_id, transaction_id=normalized_transaction_id, entity_type=normalized_entity_type, entity_id=entity_id, direction="OUTBOUND", request_reference=request_reference, status="PENDING", attempt_count=0, response_data={})
    db.add(transaction)
    db.flush()
    if commit:
        db.commit()
        db.refresh(transaction)
    return transaction


def list_integration_transactions(db: Session, facility_id: UUID, *, integration_id: UUID | None = None, status: str | None = None, limit: int = 100) -> list[IntegrationTransaction]:
    stmt = select(IntegrationTransaction).join(Integration, Integration.id == IntegrationTransaction.integration_id).where(Integration.facility_id == facility_id)
    if integration_id is not None:
        stmt = stmt.where(IntegrationTransaction.integration_id == integration_id)
    if status:
        normalized = status.strip().upper()
        if normalized not in {"PENDING", "PROCESSING", "SUCCEEDED", "FAILED", "RETRYING"}:
            raise IntegrationError("INVALID_TRANSACTION_STATUS")
        stmt = stmt.where(IntegrationTransaction.status == normalized)
    return list(db.scalars(stmt.order_by(IntegrationTransaction.created_at.desc()).limit(max(1, min(limit, 500)))))


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


def verify_callback_signature(integration: Integration, timestamp: str, signature: str, payload: dict, *, tolerance_seconds: int = 300) -> None:
    """Verify an HMAC-SHA256 payer callback using an environment-backed secret."""
    configuration = integration.configuration or {}
    secret_env = configuration.get("callback_secret_env")
    if not isinstance(secret_env, str) or not secret_env.strip():
        raise IntegrationError("CALLBACK_SECRET_ENV_NOT_CONFIGURED")
    secret = os.getenv(secret_env)
    if not secret:
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
