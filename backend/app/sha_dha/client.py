"""HTTP client for DHA AfyaLink eligibility & eClaims (public API shapes)."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from app.sha_dha import config

_log = logging.getLogger("afyasync.sha_dha")


def _headers() -> dict[str, str]:
    h = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-AfyaSync-Client": "AFYASYNC",
        "X-AfyaSync-Developer": "BAHATI-GAD-WANGWE",
    }
    tok = config.bearer_token()
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _request(
    method: str,
    path: str,
    *,
    query: dict | None = None,
    body: dict | None = None,
) -> dict[str, Any]:
    url = f"{config.base_url()}{path}"
    if query:
        url = f"{url}?{urlencode({k: v for k, v in query.items() if v is not None})}"
    data = None
    if body is not None:
        data = json.dumps(body, separators=(",", ":"), default=str).encode("utf-8")
    req = Request(url, data=data, headers=_headers(), method=method.upper())
    try:
        with urlopen(req, timeout=config.timeout_seconds()) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"raw": raw[:2000]}
            if not isinstance(parsed, dict):
                parsed = {"data": parsed}
            parsed["_http_status"] = resp.status
            return parsed
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw[:2000]}
        if not isinstance(parsed, dict):
            parsed = {"data": parsed}
        parsed["_http_status"] = exc.code
        parsed["_error"] = True
        _log.warning("afyalink_http_error path=%s status=%s", path, exc.code)
        return parsed
    except (URLError, TimeoutError, OSError) as exc:
        _log.warning("afyalink_transport path=%s err=%s", path, exc)
        return {"_error": True, "_http_status": 0, "message": str(exc)[:300]}


def check_eligibility_live(
    *,
    membership_number: str | None = None,
    national_id: str | None = None,
    patient_id: str | None = None,
) -> dict[str, Any]:
    """GET /v2/eligibility — shape from AfyaLink eligibility apidocs."""
    q: dict[str, str] = {"agent": config.agent_code()}
    if membership_number:
        q["membership_number"] = membership_number
    if national_id:
        q["id_number"] = national_id
    if patient_id:
        q["patient_id"] = patient_id
    return _request("GET", "/v2/eligibility", query=q)


def submit_claim_bundle_live(bundle: dict) -> dict[str, Any]:
    """POST /v1/shr-med/bundle — FHIR claim document."""
    return _request("POST", "/v1/shr-med/bundle", body=bundle)


def claim_status_live(*, bundle_id: str | None = None, claim_id: str | None = None) -> dict[str, Any]:
    q: dict[str, str] = {}
    if bundle_id:
        q["bundle_id"] = bundle_id
    if claim_id:
        q["claim_id"] = claim_id
    return _request("GET", "/v1/shr-med/claim-status", query=q)


def mock_eligibility(*, membership_number: str) -> dict[str, Any]:
    """Deterministic offline eligibility when live credentials are absent.

    Not a fake patient database — explicit mock mode for development/pilot wiring.
    """
    m = membership_number.strip().upper()
    # Simple rule: membership ending with 0 is ineligible (for test paths)
    eligible = not m.endswith("0") and len(m) >= 4
    return {
        "eligible": eligible,
        "eligible_flag": 1 if eligible else 0,
        "membership_number": m,
        "scheme": "SHIF",
        "scheme_category": "SOCIAL HEALTH AUTHORITY",
        "status": "ACTIVE" if eligible else "INACTIVE",
        "possible_solution": None if eligible else "Update contribution or verify membership with SHA",
        "mode": "mock",
        "message": "Mock eligibility — set SHA_DHA_MODE=live and AFYALINK_BEARER_TOKEN for production",
    }


def mock_claim_submit(bundle: dict) -> dict[str, Any]:
    bid = bundle.get("id") or str(uuid4())
    return {
        "status": "ACCEPTED",
        "bundle_id": bid,
        "mode": "mock",
        "message": "Mock claim accept — configure AfyaLink credentials for live submission",
    }


def mock_claim_status(*, bundle_id: str) -> dict[str, Any]:
    return {
        "bundle_id": bundle_id,
        "status": "UNDER_REVIEW",
        "mode": "mock",
        "message": "Mock status — live poll requires AfyaLink token",
    }
