"""Verify national modules import and critical tables exist."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

# Modules that must import cleanly (phases 0–10)
CRITICAL_IMPORTS = [
    ("identity", "app.identity.router"),
    ("can_i_get_this", "app.coverage.can_i_get_this_router"),
    ("citizen_portal", "app.portal.citizen_router"),
    ("hospital_os", "app.hospital_os.router"),
    ("clinical_safety", "app.clinical_safety.router"),
    ("lab_intelligence", "app.lab_intelligence.router"),
    ("imaging_intelligence", "app.imaging_intelligence.router"),
    ("pharmacy_supply", "app.pharmacy_supply.router"),
    ("claims_financing", "app.claims_financing.router"),
    ("hie", "app.hie.router"),
]

CRITICAL_TABLES = [
    "households",
    "membership_records",
    "identity_match_logs",
    "benefit_utilisation",
    "patient_complaints",
    "medication_safety_flags",
    "lab_test_references",
    "lab_critical_alerts",
    "imaging_test_safety",
    "imaging_critical_findings",
    "controlled_dispense_logs",
    "hie_export_logs",
    "hie_nodes",
    "hie_inbound_documents",
]

# Public route catalogue — national differentiation layer
NATIONAL_API_CATALOGUE = [
    {"phase": 1, "method": "POST", "path": "/api/v1/identity/match"},
    {"phase": 1, "method": "POST", "path": "/api/v1/identity/households"},
    {"phase": 1, "method": "POST", "path": "/api/v1/identity/memberships"},
    {"phase": 1, "method": "POST", "path": "/api/v1/identity/deceased"},
    {"phase": 1, "method": "POST", "path": "/api/v1/identity/corrections"},
    {"phase": 2, "method": "POST", "path": "/api/v1/coverage/can-i-get-this"},
    {"phase": 2, "method": "GET", "path": "/api/v1/coverage/utilisation"},
    {"phase": 3, "method": "GET", "path": "/api/v1/citizen/timeline"},
    {"phase": 3, "method": "GET", "path": "/api/v1/citizen/access-history"},
    {"phase": 3, "method": "POST", "path": "/api/v1/citizen/complaints"},
    {"phase": 4, "method": "GET", "path": "/api/v1/hospital-os/encounters/{id}/journey"},
    {"phase": 4, "method": "GET", "path": "/api/v1/hospital-os/integrity"},
    {"phase": 5, "method": "POST", "path": "/api/v1/clinical-safety/check"},
    {"phase": 5, "method": "PUT", "path": "/api/v1/clinical-safety/flags"},
    {"phase": 6, "method": "GET", "path": "/api/v1/lab-intelligence/critical"},
    {"phase": 6, "method": "GET", "path": "/api/v1/lab-intelligence/tat"},
    {"phase": 7, "method": "POST", "path": "/api/v1/imaging-intelligence/contrast-check"},
    {"phase": 7, "method": "GET", "path": "/api/v1/imaging-intelligence/critical-findings"},
    {"phase": 8, "method": "GET", "path": "/api/v1/pharmacy-supply/health"},
    {"phase": 8, "method": "GET", "path": "/api/v1/pharmacy-supply/pre-dispense/{id}"},
    {"phase": 8, "method": "GET", "path": "/api/v1/pharmacy-supply/controlled-log"},
    {"phase": 9, "method": "GET", "path": "/api/v1/claims-financing/claims/{id}/quality"},
    {"phase": 9, "method": "GET", "path": "/api/v1/claims-financing/pipeline"},
    {"phase": 9, "method": "GET", "path": "/api/v1/claims-financing/denials"},
    {"phase": 10, "method": "GET", "path": "/api/v1/hie/metadata"},
    {"phase": 10, "method": "GET", "path": "/api/v1/hie/Patient/{id}/$summary"},
    {"phase": 10, "method": "POST", "path": "/api/v1/hie/referral-package"},
    {"phase": 10, "method": "POST", "path": "/api/v1/hie/inbound"},
    {"phase": 10, "method": "GET", "path": "/api/v1/hie/nodes"},
    {"phase": 10, "method": "GET", "path": "/api/v1/hie/exports"},
]


def check_imports() -> list[dict]:
    results = []
    for name, module in CRITICAL_IMPORTS:
        try:
            __import__(module)
            results.append({"module": name, "path": module, "ok": True, "error": None})
        except Exception as exc:
            results.append({"module": name, "path": module, "ok": False, "error": str(exc)[:300]})
    return results


def check_tables(db: Session) -> list[dict]:
    results = []
    for table in CRITICAL_TABLES:
        try:
            exists = db.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = :t"
                ),
                {"t": table},
            ).scalar()
            results.append({"table": table, "ok": bool(exists)})
        except Exception as exc:
            results.append({"table": table, "ok": False, "error": str(exc)[:200]})
    return results


def national_readiness(db: Session | None = None) -> dict:
    imports = check_imports()
    tables = check_tables(db) if db is not None else []
    import_ok = all(r["ok"] for r in imports)
    table_ok = all(r.get("ok") for r in tables) if tables else None
    return {
        "program": "AFYASYNC_NATIONAL_REPLACEMENT",
        "phases_covered": "0-10",
        "developer": "BAHATI GAD WANGWE",
        "imports_ok": import_ok,
        "tables_ok": table_ok,
        "imports": imports,
        "tables": tables,
        "api_catalogue": NATIONAL_API_CATALOGUE,
        "api_count": len(NATIONAL_API_CATALOGUE),
        "notes": [
            "Run alembic upgrade head before production",
            "Auth required on all facility-scoped routes",
            "Citizen routes use patient JWT",
        ],
    }
