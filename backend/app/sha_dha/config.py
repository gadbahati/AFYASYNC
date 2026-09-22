"""Configuration for AfyaLink / SHA / DHA endpoints.

Public references (research 2026):
- Eligibility: GET {{base}}/v2/eligibility  (afyalink.dha.go.ke apidocs)
- Claims: POST {{base}}/v1/shr-med/bundle
- Status: GET {{base}}/v1/shr-med/claim-status?bundle_id=
- UAT base often: https://uat.dha.go.ke
- Credentials: developer.dha.go.ke / facility SHA onboarding
"""

from __future__ import annotations

import os


def sha_mode() -> str:
    """mock | live — live requires bearer token."""
    mode = (os.getenv("SHA_DHA_MODE") or os.getenv("AFYALINK_MODE") or "mock").strip().lower()
    return mode if mode in {"mock", "live"} else "mock"


def base_url() -> str:
    return (
        os.getenv("AFYALINK_BASE_URL")
        or os.getenv("SHA_DHA_BASE_URL")
        or "https://uat.dha.go.ke"
    ).rstrip("/")


def bearer_token() -> str | None:
    tok = (
        os.getenv("AFYALINK_BEARER_TOKEN")
        or os.getenv("SHA_DHA_BEARER_TOKEN")
        or os.getenv("DHA_API_TOKEN")
        or ""
    ).strip()
    return tok or None


def agent_code() -> str:
    return (os.getenv("AFYALINK_AGENT") or os.getenv("SHA_AGENT") or "AFYASYNC").strip()


def timeout_seconds() -> int:
    try:
        return max(5, min(int(os.getenv("SHA_DHA_TIMEOUT", "25")), 60))
    except ValueError:
        return 25


def is_live_ready() -> bool:
    return sha_mode() == "live" and bool(bearer_token())
