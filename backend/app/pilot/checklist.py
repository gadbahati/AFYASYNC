"""Pilot site operational checklist — gates before go-live."""

from __future__ import annotations

from datetime import datetime, timezone

PILOT_GATES = [
    {
        "id": "PIL-01",
        "category": "IDENTITY",
        "title": "Patient registration + Afya ID path tested",
        "required": True,
        "evidence_hint": "Create patient, issue Afya ID, login as patient",
    },
    {
        "id": "PIL-02",
        "category": "CLINICAL",
        "title": "Encounter → diagnosis → order → result path",
        "required": True,
        "evidence_hint": "One complete OP journey with lab or pharmacy",
    },
    {
        "id": "PIL-03",
        "category": "SAFETY",
        "title": "Clinical safety intercept exercised",
        "required": True,
        "evidence_hint": "Allergy or DDI WARN/BLOCK on prescribe",
    },
    {
        "id": "PIL-04",
        "category": "BILLING",
        "title": "Invoice + claim draft generated",
        "required": True,
        "evidence_hint": "Claim quality score GREEN/AMBER reviewed",
    },
    {
        "id": "PIL-05",
        "category": "CONSENT",
        "title": "Sensitive disease consent with signature",
        "required": True,
        "evidence_hint": "Consent true and false paths both tested",
    },
    {
        "id": "PIL-06",
        "category": "OFFLINE",
        "title": "Outbox enqueue + drain on pilot site",
        "required": True,
        "evidence_hint": "POST /offline/enqueue and /drain",
    },
    {
        "id": "PIL-07",
        "category": "SECURITY",
        "title": "Security posture PASS or WARN only (no CRITICAL)",
        "required": True,
        "evidence_hint": "GET /api/v1/certification/security-posture",
    },
    {
        "id": "PIL-08",
        "category": "SHA",
        "title": "SHA connector mode understood (mock vs live)",
        "required": True,
        "evidence_hint": "GET /api/v1/sha-dha/status — live only with real token",
    },
    {
        "id": "PIL-09",
        "category": "STAFF",
        "title": "Named pilot super-user + backup trained",
        "required": True,
        "evidence_hint": "Training attendance log",
    },
    {
        "id": "PIL-10",
        "category": "ROLLBACK",
        "title": "Rollback / dual-run plan documented",
        "required": True,
        "evidence_hint": "Written cutover sheet signed by facility lead",
    },
]


def pilot_checklist_template() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gates": PILOT_GATES,
        "gate_count": len(PILOT_GATES),
        "required_count": sum(1 for g in PILOT_GATES if g["required"]),
        "instruction": "Mark each gate done only with real evidence — no placeholders",
        "developer": "BAHATI GAD WANGWE",
    }
