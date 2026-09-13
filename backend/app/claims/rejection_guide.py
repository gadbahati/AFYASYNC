"""Map common claim rejection codes to actionable repair steps.

Works offline of official SHA APIs. When live SHA responses arrive,
map their codes into this table (or extend it) so staff see human guidance.
"""

from __future__ import annotations

REJECTION_GUIDE: dict[str, dict[str, str]] = {
    "COV001": {
        "title": "Coverage not verified",
        "fix": "Re-verify membership / attach verified coverage, then re-validate claim.",
        "owner": "Reception / Claims",
    },
    "COV002": {
        "title": "Membership lapsed or inactive",
        "fix": "Confirm SHA/AfyaSync status with member. Use CASH path if cover invalid.",
        "owner": "Reception",
    },
    "AUTH001": {
        "title": "Pre-authorization missing",
        "fix": "Request pre-auth for high-cost services, link authorization, rebuild claim.",
        "owner": "Clinician / Claims",
    },
    "ITEM001": {
        "title": "Service not in package / tariff",
        "fix": "Remove non-covered lines or bill patient portion; resubmit claimable lines only.",
        "owner": "Billing",
    },
    "ITEM002": {
        "title": "Duplicate service line",
        "fix": "Review claim items; remove duplicates; re-validate.",
        "owner": "Claims",
    },
    "AMT001": {
        "title": "Amount exceeds tariff",
        "fix": "Adjust unit prices to approved tariff; recreate or amend claim amount.",
        "owner": "Billing",
    },
    "DOC001": {
        "title": "Clinical documentation incomplete",
        "fix": "Complete diagnosis/notes on encounter; ensure claim items match documented care.",
        "owner": "Clinician",
    },
    "FAC001": {
        "title": "Facility not contracted for service",
        "fix": "Confirm facility contract with payer; do not resubmit until contract fixed.",
        "owner": "Admin",
    },
    "ID001": {
        "title": "Patient identity mismatch",
        "fix": "Correct national ID / membership linkage on person record; re-attach coverage.",
        "owner": "Reception",
    },
    "SYS999": {
        "title": "Payer system / temporary failure",
        "fix": "Wait and resubmit. No clinical change required.",
        "owner": "Claims",
    },
}


def guide_for(code: str | None, message: str | None = None) -> dict:
    if code and code.upper() in REJECTION_GUIDE:
        entry = REJECTION_GUIDE[code.upper()]
        return {
            "code": code.upper(),
            "title": entry["title"],
            "fix": entry["fix"],
            "owner": entry["owner"],
            "source": "AFYASYNC_GUIDE",
        }
    # Fallback from free text
    text = (message or "").lower()
    if "pre-auth" in text or "preauth" in text or "authorization" in text:
        return guide_for("AUTH001")
    if "coverage" in text or "eligib" in text or "member" in text:
        return guide_for("COV001")
    if "duplicate" in text:
        return guide_for("ITEM002")
    if "tariff" in text or "price" in text or "amount" in text:
        return guide_for("AMT001")
    return {
        "code": (code or "UNKNOWN").upper(),
        "title": "Unmapped rejection",
        "fix": message or "Review payer response message, correct data, re-validate and resubmit.",
        "owner": "Claims",
        "source": "FALLBACK",
    }
