"""Orchestrate eligibility, claim submit, status against AfyaLink."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.sha_dha import client, config
from app.sha_dha.bundle_builder import build_claim_bundle


def connection_status() -> dict:
    return {
        "mode": config.sha_mode(),
        "live_ready": config.is_live_ready(),
        "base_url": config.base_url(),
        "agent": config.agent_code(),
        "has_token": bool(config.bearer_token()),
        "endpoints": {
            "eligibility": "GET /v2/eligibility",
            "submit_claim": "POST /v1/shr-med/bundle",
            "claim_status": "GET /v1/shr-med/claim-status",
        },
        "credential_sources": [
            "https://developer.dha.go.ke",
            "https://afyalink.dha.go.ke",
            "SHA facility onboarding / provider portal credentials",
        ],
        "notes": [
            "Live calls require SHA_DHA_MODE=live and AFYALINK_BEARER_TOKEN",
            "Mock mode is explicit offline wiring — not production SHA",
        ],
        "developer": "BAHATI GAD WANGWE",
    }


def run_eligibility(
    db: Session,
    *,
    membership_number: str,
    facility_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    national_id: str | None = None,
) -> dict:
    membership = membership_number.strip().upper()
    if not membership:
        raise ValueError("MEMBERSHIP_NUMBER_REQUIRED")

    if config.is_live_ready():
        raw = client.check_eligibility_live(
            membership_number=membership,
            national_id=national_id,
        )
        if raw.get("_error"):
            raise ValueError("SHA_ELIGIBILITY_UNAVAILABLE")
        # Normalise common response shapes
        eligible_raw = raw.get("eligible", raw.get("eligible_flag", raw.get("is_eligible")))
        if eligible_raw in (1, "1", True, "true", "TRUE", "yes"):
            eligible = True
        elif eligible_raw in (0, "0", False, "false", "FALSE", "no"):
            eligible = False
        else:
            eligible = bool(eligible_raw)
        result = {
            "eligible": eligible,
            "membership_number": membership,
            "mode": "live",
            "scheme": raw.get("scheme") or raw.get("scheme_category") or "SHIF",
            "status": raw.get("status") or ("ACTIVE" if eligible else "INACTIVE"),
            "possible_solution": raw.get("possible_solution"),
            "raw_keys": sorted([k for k in raw.keys() if not str(k).startswith("_")])[:30],
        }
    else:
        result = client.mock_eligibility(membership_number=membership)

    record_audit(
        db,
        action="SHA_ELIGIBILITY_CHECK",
        resource_type="SHA_ELIGIBILITY",
        resource_id=membership[:64],
        result="ELIGIBLE" if result.get("eligible") else "INELIGIBLE",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"mode": result.get("mode")},
        commit=False,
    )
    return result


def submit_local_claim(
    db: Session,
    *,
    claim_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    bundle = build_claim_bundle(db, claim_id=claim_id, facility_id=facility_id)
    if config.is_live_ready():
        raw = client.submit_claim_bundle_live(bundle)
        if raw.get("_error"):
            raise ValueError("SHA_CLAIM_SUBMIT_FAILED")
        result = {
            "mode": "live",
            "bundle_id": raw.get("bundle_id") or bundle.get("id"),
            "status": raw.get("status") or "SUBMITTED",
            "response": {k: raw[k] for k in list(raw.keys())[:20] if not str(k).startswith("_")},
        }
    else:
        result = client.mock_claim_submit(bundle)
        result["bundle_preview_id"] = bundle.get("id")

    record_audit(
        db,
        action="SHA_CLAIM_SUBMIT",
        resource_type="CLAIM",
        resource_id=str(claim_id),
        result=str(result.get("status") or "OK")[:40],
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"mode": result.get("mode"), "bundle_id": result.get("bundle_id")},
        commit=False,
    )
    return result


def poll_claim_status(
    db: Session,
    *,
    bundle_id: str,
    facility_id: UUID | None = None,
    actor_user_id: UUID | None = None,
) -> dict:
    if not bundle_id.strip():
        raise ValueError("BUNDLE_ID_REQUIRED")
    if config.is_live_ready():
        raw = client.claim_status_live(bundle_id=bundle_id.strip())
        if raw.get("_error"):
            raise ValueError("SHA_CLAIM_STATUS_UNAVAILABLE")
        result = {
            "mode": "live",
            "bundle_id": bundle_id,
            "status": raw.get("status") or raw.get("claim_status") or "UNKNOWN",
            "response": {k: raw[k] for k in list(raw.keys())[:20] if not str(k).startswith("_")},
        }
    else:
        result = client.mock_claim_status(bundle_id=bundle_id.strip())

    record_audit(
        db,
        action="SHA_CLAIM_STATUS",
        resource_type="SHA_BUNDLE",
        resource_id=bundle_id[:64],
        result=str(result.get("status") or "OK")[:40],
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"mode": result.get("mode")},
        commit=False,
    )
    return result
