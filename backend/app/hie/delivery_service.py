"""Phase 166: real outbound HIE delivery with durable retry state."""
from __future__ import annotations
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.hie.delivery_models import HieDeliveryJob
from app.hie.auth import clear_hie_token_cache, get_hie_access_token
from app.hie.models import HieExportLog, HieNode

ACTIVE_STATUSES = {"PENDING", "RETRY"}

def queue_bundle(db: Session, *, facility_id: UUID, patient_id: UUID, destination_node_id: UUID, payload: dict, created_by: UUID | None, export_log_id: UUID | None = None) -> HieDeliveryJob:
    node = db.get(HieNode, destination_node_id)
    if node is None or node.status != "ACTIVE": raise ValueError("HIE_NODE_NOT_FOUND")
    if node.facility_id == facility_id: raise ValueError("HIE_DESTINATION_SELF")
    if node.trust_level not in {"HIGH", "NATIONAL"}: raise ValueError("HIE_DESTINATION_NOT_TRUSTED")
    if not node.endpoint_url: raise ValueError("HIE_DESTINATION_ENDPOINT_NOT_CONFIGURED")
    bundle_id = str(payload.get("id") or uuid4())
    key = f"{destination_node_id}:{bundle_id}"
    existing = db.scalar(select(HieDeliveryJob).where(HieDeliveryJob.idempotency_key == key))
    if existing is not None: return existing
    job = HieDeliveryJob(facility_id=facility_id, patient_id=patient_id, destination_node_id=destination_node_id, export_log_id=export_log_id, idempotency_key=key, payload=payload, created_by=created_by)
    db.add(job); db.flush()
    record_audit(db, action="HIE_OUTBOUND_QUEUED", resource_type="HIE_DELIVERY_JOB", resource_id=str(job.id), result="SUCCESS", user_id=created_by, facility_id=facility_id, patient_id=patient_id, metadata={"destination_node_id": str(destination_node_id), "bundle_id": bundle_id}, commit=False)
    return job

def _backoff(attempts: int) -> timedelta:
    return timedelta(seconds=min(3600, 30 * (2 ** max(0, attempts - 1))))

def deliver_job(db: Session, *, job_id: UUID, facility_id: UUID, actor_user_id: UUID | None = None) -> dict:
    job = db.get(HieDeliveryJob, job_id)
    if job is None or job.facility_id != facility_id: raise ValueError("HIE_DELIVERY_JOB_NOT_FOUND")
    if job.status == "DELIVERED": return _result(job)
    if job.status == "DEAD": raise ValueError("HIE_DELIVERY_JOB_DEAD")
    node = db.get(HieNode, job.destination_node_id)
    if node is None or node.status != "ACTIVE": raise ValueError("HIE_DESTINATION_NOT_FOUND")
    if not node.endpoint_url: raise ValueError("HIE_DESTINATION_ENDPOINT_NOT_CONFIGURED")
    job.attempts += 1
    token = get_hie_access_token()
    if token is None:
        token = os.getenv("HIE_OUTBOUND_BEARER_TOKEN", "").strip()
    headers = {"Content-Type": "application/fhir+json", "Accept": "application/fhir+json", "Idempotency-Key": job.idempotency_key}
    if token: headers["Authorization"] = f"Bearer {token}"
    timeout = float(os.getenv("HIE_OUTBOUND_TIMEOUT_SECONDS", "15"))
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response = client.post(node.endpoint_url, json=job.payload, headers=headers)
            if response.status_code == 401 and headers.get("Authorization"):
                clear_hie_token_cache()
                refreshed = get_hie_access_token()
                if refreshed:
                    headers["Authorization"] = f"Bearer {refreshed}"
                    response = client.post(node.endpoint_url, json=job.payload, headers=headers)
        job.last_http_status = response.status_code
        if 200 <= response.status_code < 300:
            job.status = "DELIVERED"; job.delivered_at = datetime.now(timezone.utc); job.last_error = None
            record_audit(db, action="HIE_OUTBOUND_DELIVERED", resource_type="HIE_DELIVERY_JOB", resource_id=str(job.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=job.patient_id, metadata={"http_status": response.status_code, "attempts": job.attempts}, commit=False)
        elif response.status_code in {408, 409, 425, 429} or response.status_code >= 500:
            if job.attempts >= job.max_attempts: job.status = "DEAD"
            else: job.status = "RETRY"; job.next_attempt_at = datetime.now(timezone.utc) + _backoff(job.attempts)
            job.last_error = response.text[:1000]
        else:
            job.status = "FAILED"; job.last_error = response.text[:1000]
    except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as exc:
        if job.attempts >= job.max_attempts: job.status = "DEAD"
        else: job.status = "RETRY"; job.next_attempt_at = datetime.now(timezone.utc) + _backoff(job.attempts)
        job.last_error = str(exc)[:1000]
    db.flush()
    return _result(job)

def _result(job: HieDeliveryJob) -> dict:
    return {"id": str(job.id), "status": job.status, "attempts": job.attempts, "max_attempts": job.max_attempts, "next_attempt_at": job.next_attempt_at.isoformat() if job.next_attempt_at else None, "last_http_status": job.last_http_status, "last_error": job.last_error, "delivered_at": job.delivered_at.isoformat() if job.delivered_at else None, "destination_node_id": str(job.destination_node_id)}

def list_jobs(db: Session, facility_id: UUID, *, limit: int = 50) -> list[HieDeliveryJob]:
    return list(db.scalars(select(HieDeliveryJob).where(HieDeliveryJob.facility_id == facility_id).order_by(HieDeliveryJob.created_at.desc()).limit(min(max(limit,1),200))))
