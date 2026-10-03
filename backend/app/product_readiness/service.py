from datetime import datetime, timezone
import importlib

from sqlalchemy.orm import Session


def _module_status(module_name: str) -> dict:
    """Report implementation presence without pretending it proves certification or live integration."""
    try:
        importlib.import_module(module_name)
        return {"status": "IMPLEMENTED", "module": module_name}
    except Exception as exc:
        return {"status": "NOT_VERIFIED", "module": module_name, "error": str(exc)[:180]}


def _capability_matrix() -> dict:
    capabilities = {
        "facility_operations": "app.hospital_os",
        "patient_registry": "app.patients",
        "clinical_encounters": "app.encounters",
        "laboratory": "app.laboratory",
        "pharmacy": "app.pharmacy",
        "appointments": "app.appointments",
        "billing_and_cash": "app.billing",
        "multi_payer_financing": "app.coverage.payer_admin_service",
        "claims_and_adjudication": "app.claims",
        "revenue_intelligence": "app.financial_intelligence",
        "offline_first": "app.offline",
        "patient_portal": "app.portal",
        "health_information_exchange": "app.hie",
        "interoperability": "app.interoperability",
        "consent_and_privacy": "app.consent",
        "identity": "app.identity",
        "audit_and_security": "app.audit",
        "multi_tenancy": "app.tenancy",
        "business_continuity": "app.business_continuity",
        "disaster_recovery": "app.disaster_recovery",
        "national_reporting": "app.reports",
        "national_operations": "app.national_ops",
    }
    return {name: _module_status(module) for name, module in capabilities.items()}


def _integration_posture() -> dict:
    from app.sha_dha import config as sha_config

    return {
        "sha_mode": sha_config.sha_mode(),
        "sha_live_ready": sha_config.is_live_ready(),
        "sha_is_required_for_core_cash": False,
        "offline_queue_available": _module_status("app.offline")["status"] == "IMPLEMENTED",
        "hie_module_available": _module_status("app.hie")["status"] == "IMPLEMENTED",
        "note": "Live external connectivity and certification still require external credentials, testing and approval.",
    }


def final_readiness(db: Session) -> dict:
    from app.national_audit.service import audit
    from app.end_to_end_simulation.service import run_simulation
    from app.production_hardening.service import hardening_manifest
    from app.disaster_recovery.service import posture

    evidence = {
        "national_audit": audit(db),
        "simulation": run_simulation(db),
        "production_hardening": hardening_manifest(),
        "disaster_recovery": posture(db),
    }
    blockers = []
    if evidence["national_audit"]["overall"] != "PASS":
        blockers.append("NATIONAL_AUDIT")
    if evidence["simulation"]["overall"] != "PASS":
        blockers.append("END_TO_END_SIMULATION")
    if evidence["production_hardening"]["overall"] != "HARDENED":
        blockers.append("PRODUCTION_HARDENING")
    if evidence["disaster_recovery"].get("band") == "RED":
        blockers.append("DISASTER_RECOVERY")

    return {
        "phase": 125,
        "product": "AfyaSync",
        "release_gate": "GO" if not blockers else "HOLD",
        "software_readiness": "READY" if not blockers else "REMEDIATION_REQUIRED",
        "blockers": blockers,
        "evidence": evidence,
        "capability_matrix": _capability_matrix(),
        "integration_posture": _integration_posture(),
        "external_gates": [
            "DHA certification and test evidence",
            "ODPC/data-protection obligations and DPIA evidence",
            "External penetration testing",
            "Live national HIE/SHA credentials and connectivity validation",
            "County/national operational sign-off",
            "Measured national-scale load and recovery tests",
        ],
        "statement": "Software readiness is not a certification or government approval. Capability presence is not proof of live external connectivity.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
