"""Sandbox handlers — deterministic, no live SHA side effects."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.partner_sandbox.models import PartnerInterest


class SandboxError(ValueError):
    pass


def sandbox_eligibility(*, member_id: str | None, national_id: str | None) -> dict:
    mid = (member_id or "").strip()
    nid = (national_id or "").strip()
    if not mid and not nid:
        raise SandboxError("MEMBER_OR_NATIONAL_ID_REQUIRED")
    # Deterministic sandbox: even last digit of id => eligible
    key = mid or nid
    eligible = bool(key) and (ord(key[-1]) % 2 == 0)
    return {
        "eligible": eligible,
        "scheme": "SHA_SANDBOX",
        "mode": "sandbox",
        "member_ref": mid or None,
        "message": "Sandbox eligibility only — not a production SHA decision",
        "developer": "BAHATI GAD WANGWE",
    }


def sandbox_claim_preflight(*, sample: bool = True) -> dict:
    findings = [
        {"code": "SANDBOX_OK", "severity": "INFO", "detail": "Sample claim structure accepted"},
        {"code": "DIAGNOSIS_PRESENT", "severity": "INFO", "detail": "Diagnosis codes present in sample"},
    ]
    return {
        "band": "GREEN",
        "findings": findings,
        "mode": "sandbox",
        "sample": sample,
        "message": "Sandbox preflight — run real preflight on production claims module",
        "developer": "BAHATI GAD WANGWE",
    }


def sandbox_hie_echo(*, note: str | None = None) -> dict:
    return {
        "echo": {
            "resourceType": "Bundle",
            "type": "document",
            "note": (note or "sandbox")[:200],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "consent_required": True,
        "mode": "sandbox",
        "developer": "BAHATI GAD WANGWE",
    }


def register_interest(
    db: Session,
    *,
    organisation: str,
    contact_email: str,
    use_case: str,
    contact_phone: str | None = None,
    facility_id: UUID | None = None,
) -> PartnerInterest:
    org = organisation.strip()
    email = contact_email.strip().lower()
    use = use_case.strip()
    if not org or not email or not use:
        raise SandboxError("ORGANISATION_EMAIL_USE_CASE_REQUIRED")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise SandboxError("INVALID_EMAIL")

    row = PartnerInterest(
        organisation=org[:200],
        contact_email=email[:200],
        contact_phone=(contact_phone or "").strip()[:40] or None,
        use_case=use[:500],
        facility_id=facility_id,
        status="RECEIVED",
    )
    db.add(row)
    db.flush()
    return row
