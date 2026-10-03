from datetime import datetime, timezone

from sqlalchemy.orm import Session

def run_simulation(db: Session) -> dict:
    stages=[]
    def stage(name, fn):
        try:
            result=fn()
            stages.append({"id":name,"status":"PASS","detail":result})
        except Exception as exc:
            stages.append({"id":name,"status":"FAIL","detail":f"{type(exc).__name__}: {str(exc)[:240]}"})

    from app.production.service import production_readiness
    from app.observability.service import evaluate_slos
    from app.disaster_recovery.service import posture
    from app.national_audit.service import audit

    stage("PLATFORM_READINESS", production_readiness)
    stage("OBSERVABILITY", evaluate_slos)
    stage("DISASTER_RECOVERY", lambda: posture(db))
    stage("NATIONAL_AUDIT", lambda: audit(db))

    failed=[x["id"] for x in stages if x["status"]!="PASS"]
    return {
        "phase":122,
        "simulation":"NON_DESTRUCTIVE",
        "overall":"PASS" if not failed else "FAIL",
        "failed_stages":failed,
        "stages":stages,
        "warning":"This does not create synthetic clinical records or prove external HIE/SHA/DHA connectivity.",
        "generated_at":datetime.now(timezone.utc).isoformat(),
    }
