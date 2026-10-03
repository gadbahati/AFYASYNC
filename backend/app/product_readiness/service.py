from datetime import datetime, timezone

from sqlalchemy.orm import Session

def final_readiness(db:Session)->dict:
    from app.national_audit.service import audit
    from app.end_to_end_simulation.service import run_simulation
    from app.production_hardening.service import hardening_manifest
    from app.disaster_recovery.service import posture

    evidence={
        "national_audit":audit(db),
        "simulation":run_simulation(db),
        "production_hardening":hardening_manifest(),
        "disaster_recovery":posture(db),
    }
    blockers=[]
    if evidence["national_audit"]["overall"]!="PASS": blockers.append("NATIONAL_AUDIT")
    if evidence["simulation"]["overall"]!="PASS": blockers.append("END_TO_END_SIMULATION")
    if evidence["production_hardening"]["overall"]!="HARDENED": blockers.append("PRODUCTION_HARDENING")
    if evidence["disaster_recovery"].get("band")=="RED": blockers.append("DISASTER_RECOVERY")

    return {
        "phase":124,
        "product":"AfyaSync",
        "release_gate":"GO" if not blockers else "HOLD",
        "software_readiness":"READY" if not blockers else "REMEDIATION_REQUIRED",
        "blockers":blockers,
        "evidence":evidence,
        "external_gates":[
            "DHA certification and test evidence",
            "ODPC/data-protection obligations and DPIA evidence",
            "External penetration testing",
            "Live national HIE/SHA credentials and connectivity validation",
            "County/national operational sign-off",
            "Measured national-scale load and recovery tests",
        ],
        "statement":"Software readiness is not a certification or government approval.",
        "generated_at":datetime.now(timezone.utc).isoformat(),
    }
