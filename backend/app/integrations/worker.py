from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing.models import Invoice, Payment
from app.claims.service import ClaimsError, build_claim_submission_payload
from app.integrations.adapters import IntegrationAdapter, build_adapter
from app.integrations.models import Integration, IntegrationTransaction
from app.preauthorizations.models import PreAuthorization

MAX_INTEGRATION_ATTEMPTS = 5
RETRY_DELAYS_SECONDS = (30, 120, 600, 1800, 3600)
PROCESSING_LEASE_SECONDS = 300


def _build_payment_submission_payload(db: Session, payment_id, facility_id):
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise ValueError("PAYMENT_NOT_FOUND")
    if payment.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")
    invoice = db.get(Invoice, payment.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise ValueError("INVOICE_NOT_FOUND")
    return {"transaction_id": payment.transaction_id, "entity_type": "PAYMENT", "payment_id": str(payment.id), "invoice_id": str(invoice.id), "invoice_number": invoice.invoice_id, "patient_id": str(payment.patient_id), "amount": str(payment.amount), "payment_method": payment.payment_method, "provider": payment.provider, "external_reference": payment.external_reference}


def _build_preauthorization_submission_payload(db: Session, authorization_id, facility_id):
    authorization = db.get(PreAuthorization, authorization_id)
    if authorization is None:
        raise ValueError("PREAUTH_NOT_FOUND")
    if authorization.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")
    if authorization.status != "SUBMITTED":
        raise ValueError("PREAUTH_NOT_SUBMITTED")
    return {"authorization_id": str(authorization.id), "authorization_number": authorization.authorization_number, "patient_id": str(authorization.patient_id), "encounter_id": str(authorization.encounter_id) if authorization.encounter_id else None, "coverage_id": str(authorization.coverage_id), "payer_id": str(authorization.payer_id), "benefit_package_code": authorization.benefit_package_code, "care_setting": authorization.care_setting, "department": authorization.department, "requested_amount": str(authorization.requested_amount), "requested_services": authorization.requested_services}


def _build_payload(db: Session, transaction: IntegrationTransaction, facility_id):
    if transaction.entity_type == "CLAIM":
        if transaction.entity_id is None:
            raise ValueError("CLAIM_REFERENCE_REQUIRED")
        return build_claim_submission_payload(db, transaction.entity_id, facility_id)
    if transaction.entity_type == "PAYMENT":
        if transaction.entity_id is None:
            raise ValueError("PAYMENT_REFERENCE_REQUIRED")
        return _build_payment_submission_payload(db, transaction.entity_id, facility_id)
    if transaction.entity_type == "PREAUTHORIZATION":
        if transaction.entity_id is None:
            raise ValueError("PREAUTH_REFERENCE_REQUIRED")
        return _build_preauthorization_submission_payload(db, transaction.entity_id, facility_id)
    raise ValueError("UNSUPPORTED_OUTBOUND_ENTITY")


def _record_failure(db: Session, transaction_id, code: str, response_data: dict | None = None) -> IntegrationTransaction:
    transaction = db.scalar(select(IntegrationTransaction).where(IntegrationTransaction.id == transaction_id).with_for_update())
    if transaction is None:
        raise ValueError("TRANSACTION_NOT_FOUND")
    transaction.attempt_count += 1
    transaction.last_attempt_at = datetime.now(timezone.utc)
    transaction.response_code = code
    transaction.response_data = response_data or {}
    transaction.status = "RETRYING" if transaction.attempt_count < MAX_INTEGRATION_ATTEMPTS else "FAILED"
    db.commit()
    db.refresh(transaction)
    return transaction


def process_pending_transaction(db: Session, transaction_id, adapter: IntegrationAdapter | None = None) -> IntegrationTransaction:
    now = datetime.now(timezone.utc)
    transaction = db.scalar(select(IntegrationTransaction).where(IntegrationTransaction.id == transaction_id).with_for_update())
    if transaction is None:
        raise ValueError("TRANSACTION_NOT_FOUND")
    if transaction.direction != "OUTBOUND":
        return transaction
    integration = db.get(Integration, transaction.integration_id)
    if integration is None:
        raise ValueError("INTEGRATION_NOT_FOUND")
    if integration.status != "ACTIVE":
        raise ValueError("INTEGRATION_NOT_ACTIVE")

    if transaction.status == "PROCESSING":
        if transaction.last_attempt_at is None or now - transaction.last_attempt_at <= timedelta(seconds=PROCESSING_LEASE_SECONDS):
            return transaction
        transaction.status = "RETRYING"
        db.flush()

    if transaction.status not in {"PENDING", "RETRYING"}:
        return transaction
    if transaction.attempt_count >= MAX_INTEGRATION_ATTEMPTS:
        transaction.status = "FAILED"
        transaction.response_code = "MAX_ATTEMPTS_EXCEEDED"
        transaction.response_data = {"max_attempts": MAX_INTEGRATION_ATTEMPTS}
        db.commit(); db.refresh(transaction); return transaction
    if transaction.status == "RETRYING" and transaction.last_attempt_at is not None:
        delay = RETRY_DELAYS_SECONDS[min(max(transaction.attempt_count - 1, 0), len(RETRY_DELAYS_SECONDS) - 1)]
        if now < transaction.last_attempt_at + timedelta(seconds=delay):
            return transaction

    try:
        payload = _build_payload(db, transaction, integration.facility_id)
    except (ClaimsError, ValueError) as exc:
        return _record_failure(db, transaction.id, str(exc))

    try:
        adapter = adapter or build_adapter(integration.configuration)
    except ValueError as exc:
        return _record_failure(db, transaction.id, str(exc))

    transaction.status = "PROCESSING"
    transaction.last_attempt_at = now
    db.commit()

    try:
        result = adapter.send(payload, transaction.transaction_id)
    except Exception as exc:
        return _record_failure(db, transaction.id, "ADAPTER_EXCEPTION", {"error_type": type(exc).__name__})

    finalized = db.scalar(select(IntegrationTransaction).where(IntegrationTransaction.id == transaction.id).with_for_update())
    if finalized is None:
        raise ValueError("TRANSACTION_NOT_FOUND")
    if finalized.status != "PROCESSING":
        db.rollback()
        return finalized
    if result.status not in {"SUCCEEDED", "FAILED", "RETRYING", "PENDING", "PROCESSING"}:
        finalized.status = "FAILED"
        finalized.response_code = "INVALID_ADAPTER_STATUS"
        finalized.response_data = {}
    else:
        finalized.status = result.status
        finalized.response_code = result.response_code
        finalized.external_reference = result.external_reference
        finalized.response_data = result.response_data or {}
    finalized.attempt_count += 1
    finalized.last_attempt_at = datetime.now(timezone.utc)
    if finalized.status in {"PENDING", "PROCESSING"} and finalized.attempt_count >= MAX_INTEGRATION_ATTEMPTS:
        finalized.status = "FAILED"
        finalized.response_code = "MAX_ATTEMPTS_EXCEEDED"
        finalized.response_data = {"max_attempts": MAX_INTEGRATION_ATTEMPTS}
    db.commit()
    db.refresh(finalized)
    return finalized


def list_retryable_transactions(db: Session, limit: int = 100) -> list[IntegrationTransaction]:
    now = datetime.now(timezone.utc)
    rows = list(db.scalars(select(IntegrationTransaction).where(IntegrationTransaction.direction == "OUTBOUND", IntegrationTransaction.status.in_(["PENDING", "RETRYING"]), IntegrationTransaction.attempt_count < MAX_INTEGRATION_ATTEMPTS).order_by(IntegrationTransaction.created_at).limit(max(1, min(limit, 500)))))
    retryable = []
    for transaction in rows:
        if transaction.status == "PENDING" or transaction.last_attempt_at is None:
            retryable.append(transaction)
            continue
        delay = RETRY_DELAYS_SECONDS[min(max(transaction.attempt_count - 1, 0), len(RETRY_DELAYS_SECONDS) - 1)]
        if now >= transaction.last_attempt_at + timedelta(seconds=delay):
            retryable.append(transaction)
    return retryable
