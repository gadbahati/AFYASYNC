"""DHA certification evidence assembly & submission kit (Phase 30).

Produces a single auditor-facing bundle that points to live evidence
endpoints. This is not a DHA certificate — it is submission readiness.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.certification.checklist import CERTIFICATION_DOMAINS, summarise_checklist
from app.certification.security_posture import security_posture


def _control_stats() -> dict:
    summary = summarise_checklist()
    return summary


def submission_kit() -> dict:
    summary = _control_stats()
    posture = security_posture()

    # Map domain implementation rates
    domain_rows = []
    for domain in CERTIFICATION_DOMAINS:
        controls = domain.get("controls") or []
        implemented = sum(1 for c in controls if str(c.get("status", "")).upper() == "IMPLEMENTED")
        total = len(controls)
        pct = round(100.0 * implemented / total, 1) if total else 0.0
        domain_rows.append(
            {
                "domain": domain.get("domain"),
                "title": domain.get("title"),
                "implemented": implemented,
                "total": total,
                "pct": pct,
            }
        )

    operator_actions = [
        {
            "id": "OA-01",
            "action": "Obtain production SHA/DHA API credentials and set SHA_DHA_MODE=live",
            "owner": "OPERATOR",
            "blocks_cert": False,
            "blocks_live_claims": True,
        },
        {
            "id": "OA-02",
            "action": "Commission independent penetration test; attach report PDF",
            "owner": "EXTERNAL",
            "blocks_cert": True,
            "blocks_live_claims": False,
        },
        {
            "id": "OA-03",
            "action": "Submit evidence pack to DHA certification portal",
            "owner": "OPERATOR",
            "blocks_cert": True,
            "blocks_live_claims": False,
        },
        {
            "id": "OA-04",
            "action": "Complete pilot at ≥1 county with rollout/pilot-evidence snapshot",
            "owner": "OPERATOR",
            "blocks_cert": False,
            "blocks_live_claims": False,
        },
        {
            "id": "OA-05",
            "action": "Confirm production JWT secret strength and CORS allowlist",
            "owner": "OPERATOR",
            "blocks_cert": True,
            "blocks_live_claims": True,
        },
    ]

    evidence_index = [
        {"ref": "CERT-EVIDENCE", "path": "/api/v1/certification/evidence"},
        {"ref": "SECURITY-POSTURE", "path": "/api/v1/certification/security-posture"},
        {"ref": "SECURITY-OPS-CHECKLIST", "path": "/api/v1/security-ops/checklist"},
        {"ref": "ACCESS-REVIEW", "path": "/api/v1/security-ops/access-review"},
        {"ref": "RELIABILITY-MATRIX", "path": "/api/v1/reliability/readiness-matrix"},
        {"ref": "FRAUD-SCAN", "path": "/api/v1/fraud-integrity/facility-scan"},
        {"ref": "QUALITY-SCORECARD", "path": "/api/v1/quality/facility-scorecard"},
        {"ref": "ONBOARDING-KIT", "path": "/api/v1/onboarding/facility-kit"},
        {"ref": "PILOT-EVIDENCE", "path": "/api/v1/rollout/pilot-evidence"},
        {"ref": "COUNTY-ROLLOUT", "path": "/api/v1/rollout/county-dashboard"},
        {"ref": "WAREHOUSE-FACTS", "path": "/api/v1/warehouse/facts"},
        {"ref": "TRAINING-CATALOG", "path": "/api/v1/training/catalog"},
        {"ref": "SUBMISSION-KIT", "path": "/api/v1/certification/submission-kit"},
    ]

    posture_ok = all(c.get("ok") for c in (posture.get("checks") or []) if c.get("severity") in {"CRITICAL", "HIGH"})

    readiness = {
        "software_controls_ready": True,
        "security_posture_high_severity_ok": posture_ok,
        "external_pen_test": False,
        "dha_portal_submission": False,
        "live_sha_credentials": False,
    }

    # Overall gate: software ready; external items still open
    software_score = summary.get("implemented_pct") if isinstance(summary, dict) else None
    if software_score is None and isinstance(summary, dict):
        # try alternate keys from summarise_checklist
        software_score = summary.get("pct") or summary.get("score_pct")

    return {
        "program": "AFYASYNC_NATIONAL_REPLACEMENT",
        "phase": 30,
        "title": "DHA certification evidence assembly & submission kit",
        "checklist_summary": summary,
        "domains": domain_rows,
        "security_posture_snapshot": posture,
        "evidence_index": evidence_index,
        "operator_actions": operator_actions,
        "readiness": readiness,
        "submission_notes": [
            "Attach JSON from /api/v1/certification/evidence as control map",
            "Attach /api/v1/certification/security-posture for runtime config checks",
            "Attach pilot evidence + county dashboard exports for field proof",
            "Attach independent pen-test PDF when available",
            "Register system on DHA certification portal per current DHA process",
        ],
        "disclaimer": "This kit organises evidence for DHA review — it is not a DHA certificate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
