"""Published integration contracts for partners (sandbox-first)."""

from __future__ import annotations

from datetime import datetime, timezone

PARTNER_CONTRACTS = [
    {
        "id": "CTR-ELIGIBILITY",
        "name": "Coverage eligibility check",
        "version": "1.0",
        "methods": ["POST"],
        "sandbox_path": "/api/v1/partner-sandbox/eligibility",
        "production_paths": ["/api/v1/coverage/sha-eligibility", "/api/v1/sha-dha/eligibility"],
        "auth": "Bearer facility JWT",
        "request": {"member_id": "string", "national_id": "string optional"},
        "response": {"eligible": "bool", "scheme": "string", "mode": "mock|live"},
    },
    {
        "id": "CTR-CLAIM-PREFLIGHT",
        "name": "Claim quality preflight",
        "version": "1.0",
        "methods": ["POST"],
        "sandbox_path": "/api/v1/partner-sandbox/claim-preflight",
        "production_paths": ["/api/v1/claims/preflight"],
        "auth": "Bearer facility JWT",
        "request": {"claim_id": "uuid optional", "sample": "bool"},
        "response": {"band": "GREEN|AMBER|RED", "findings": "array"},
    },
    {
        "id": "CTR-FACILITY-REGISTER",
        "name": "Partner facility handshake",
        "version": "1.0",
        "methods": ["POST"],
        "sandbox_path": "/api/v1/partner-sandbox/register-interest",
        "production_paths": [],
        "auth": "Bearer facility JWT (or national ops)",
        "request": {"organisation": "string", "contact_email": "string", "use_case": "string"},
        "response": {"registration_id": "uuid", "status": "RECEIVED"},
    },
    {
        "id": "CTR-HIE-BUNDLE",
        "name": "HIE document reference",
        "version": "1.0",
        "methods": ["GET"],
        "sandbox_path": "/api/v1/partner-sandbox/hie-echo",
        "production_paths": ["/api/v1/hie/"],
        "auth": "Bearer facility JWT",
        "request": {"note": "Sandbox returns structured echo only"},
        "response": {"echo": "object", "consent_required": True},
    },
]


def contracts_catalogue() -> dict:
    return {
        "contracts": PARTNER_CONTRACTS,
        "sandbox_base": "/api/v1/partner-sandbox",
        "rules": [
            "Sandbox never calls live SHA production endpoints",
            "Partners must complete onboarding before live credentials",
            "All traffic audited; no PHI in sandbox sample payloads",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
