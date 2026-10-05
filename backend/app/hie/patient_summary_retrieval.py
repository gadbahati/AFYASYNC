"""Phase 203: governed retrieval of a prior Kenya Patient Summary from a trusted HIE node."""
from __future__ import annotations
import os
from datetime import datetime, timezone
from uuid import UUID
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.hie.auth import clear_hie_token_cache, get_hie_access_token
from app.hie.conformance import assert_valid_bundle
from app.hie.consent_models import HieConsent
from app.hie.models import HieNode
from app.patients.models import AfyaIdentity, PatientFacility, Person

class PatientSummaryRetrievalError(ValueError):
    pass

def retrieve_patient_summary_from_hie(db: Session, *, patient_id: UUID, facility_id: UUID, source_node_id: UUID, actor_user_id: UUID | None, purpose_of_use: str = "TREATMENT") -> dict:
    purpose = purpose_of_use.strip().upper()
    if purpose not in {"TREATMENT", "PAYMENT", "PUBLICHEALTH", "OPERATIONS"}:
        raise PatientSummaryRetrievalError("INVALID_PURPOSE_OF_USE")
    enrolled = db.scalar(select(PatientFacility).where(PatientFacility.patient_id == patient_id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE"))
    person = db.get(Person, patient_id)
    identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == patient_id, AfyaIdentity.status == "ACTIVE"))
    if enrolled is None or person is None:
        raise PatientSummaryRetrievalError("PATIENT_NOT_ENROLLED_AT_FACILITY")
    if enrolled is None:
        raise PatientSummaryRetrievalError("PATIENT_NOT_ENROLLED_AT_FACILITY")
    node = db.get(HieNode, source_node_id)
    if node is None or node.status != "ACTIVE":
        raise PatientSummaryRetrievalError("HIE_SOURCE_NODE_NOT_FOUND")
    if node.facility_id == facility_id:
        raise PatientSummaryRetrievalError("HIE_SOURCE_SELF")
    if node.trust_level not in {"HIGH", "NATIONAL"}:
        raise PatientSummaryRetrievalError("HIE_SOURCE_NOT_TRUSTED")
    if not node.endpoint_url:
        raise PatientSummaryRetrievalError("HIE_SOURCE_ENDPOINT_NOT_CONFIGURED")
    now = datetime.now(timezone.utc)
    consent = db.scalar(select(HieConsent).where(
        HieConsent.patient_id == patient_id,
        HieConsent.facility_id == facility_id,
        HieConsent.status == "ACTIVE",
        HieConsent.decision == "PERMIT",
        HieConsent.scope == "HIE_SHARE",
        HieConsent.purpose == purpose,
        (HieConsent.recipient_node_id == source_node_id) | HieConsent.recipient_node_id.is_(None),
    ).order_by(HieConsent.created_at.desc()))
    if consent is None:
        raise PatientSummaryRetrievalError("HIE_PATIENT_CONSENT_REQUIRED")
    if consent.period_start and consent.period_start > now:
        raise PatientSummaryRetrievalError("HIE_CONSENT_NOT_YET_ACTIVE")
    if consent.period_end and consent.period_end < now:
        raise PatientSummaryRetrievalError("HIE_CONSENT_EXPIRED")
    if consent.revoked_at and consent.revoked_at <= now:
        raise PatientSummaryRetrievalError("HIE_CONSENT_REVOKED")
    base = node.endpoint_url.rstrip("/")
    url = f"{base}/Patient/{patient_id}/$summary"
    token = get_hie_access_token() or os.getenv("HIE_OUTBOUND_BEARER_TOKEN", "").strip()
    headers = {"Accept": "application/fhir+json"}
    facility_registry_code = os.getenv("HIE_FACILITY_REGISTRY_CODE", "").strip()
    if facility_registry_code:
        headers["X-Facility-Id"] = facility_registry_code
        headers["X-Facility-Id-Type"] = "fr-code"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    timeout = float(os.getenv("HIE_OUTBOUND_TIMEOUT_SECONDS", "15"))
    try:
        with httpx.Client(timeout=timeout, follow_redirects=False) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 401 and headers.get("Authorization"):
                clear_hie_token_cache()
                refreshed = get_hie_access_token()
                if refreshed:
                    headers["Authorization"] = f"Bearer {refreshed}"
                    response = client.get(url, headers=headers)
    except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError) as exc:
        record_audit(db, action="HIE_PATIENT_SUMMARY_RETRIEVE", resource_type="Patient", resource_id=str(patient_id), result="FAILED", user_id=actor_user_id, facility_id=facility_id, patient_id=patient_id, metadata={"source_node_id": str(source_node_id), "error": type(exc).__name__}, commit=False)
        raise PatientSummaryRetrievalError("HIE_SUMMARY_RETRIEVAL_NETWORK_ERROR") from exc
    if response.status_code < 200 or response.status_code >= 300:
        record_audit(db, action="HIE_PATIENT_SUMMARY_RETRIEVE", resource_type="Patient", resource_id=str(patient_id), result="FAILED", user_id=actor_user_id, facility_id=facility_id, patient_id=patient_id, metadata={"source_node_id": str(source_node_id), "http_status": response.status_code}, commit=False)
        raise PatientSummaryRetrievalError(f"HIE_SUMMARY_RETRIEVAL_HTTP_{response.status_code}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise PatientSummaryRetrievalError("HIE_SUMMARY_INVALID_JSON") from exc
    if not isinstance(payload, dict) or payload.get("resourceType") != "Bundle":
        raise PatientSummaryRetrievalError("HIE_SUMMARY_BUNDLE_REQUIRED")
    if payload.get("type") != "document":
        raise PatientSummaryRetrievalError("HIE_SUMMARY_DOCUMENT_BUNDLE_REQUIRED")
    entries = payload.get("entry") or []
    if not entries or not isinstance(entries[0], dict) or (entries[0].get("resource") or {}).get("resourceType") != "Composition":
        raise PatientSummaryRetrievalError("HIE_SUMMARY_COMPOSITION_FIRST_REQUIRED")
    patients = [e.get("resource") for e in entries if isinstance(e, dict) and isinstance(e.get("resource"), dict) and e["resource"].get("resourceType") == "Patient"]
    if not patients:
        raise PatientSummaryRetrievalError("HIE_SUMMARY_PATIENT_REQUIRED")
    remote_ids = {(str(i.get("system") or ""), str(i.get("value") or "")) for p in patients for i in (p.get("identifier") or []) if isinstance(i, dict) and i.get("value")}
    expected = set()
    if identity and identity.afya_id:
        expected.add(("https://afyasync.health.ke/identifier/afya-id", str(identity.afya_id)))
    if all(str(p.get("id") or "") != str(patient_id) for p in patients) and not (remote_ids & expected):
        raise PatientSummaryRetrievalError("HIE_SUMMARY_PATIENT_IDENTITY_MISMATCH")
    try:
        assert_valid_bundle(payload, require_provenance=False)
    except ValueError as exc:
        raise PatientSummaryRetrievalError(str(exc)) from exc
    record_audit(db, action="HIE_PATIENT_SUMMARY_RETRIEVE", resource_type="Patient", resource_id=str(patient_id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=patient_id, metadata={"source_node_id": str(source_node_id), "resource_count": len(entries), "http_status": response.status_code, "purpose_of_use": purpose}, commit=False)
    return payload
