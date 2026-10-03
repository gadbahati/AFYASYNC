import os
from datetime import datetime, timezone

from app.config import settings

def hardening_manifest() -> dict:
    checks=[
        {"id":"ENVIRONMENT","pass":settings.environment=="production","detail":f"environment={settings.environment}"},
        {"id":"DATABASE_URL","pass":bool(settings.database_url),"detail":"Database connection configured"},
        {"id":"CORS","pass":bool(settings.cors_origin_list()),"detail":"Explicit CORS origins configured"},
        {"id":"SECRET_KEY","pass":bool(getattr(settings,"jwt_secret",None)),"detail":"Application signing secret configured"},
        {"id":"DEBUG","pass":not bool(getattr(settings,"debug",False)),"detail":"Debug mode disabled"},
        {"id":"SEED_GUARD","pass":not (os.getenv("SEED_UNIVERSAL_ADMIN","").strip().lower() in {"1","true","yes"} and settings.environment=="production"),"detail":"Production universal-admin seed guard"},
    ]
    failed=[c["id"] for c in checks if not c["pass"]]
    return {
        "phase":123,
        "overall":"HARDENED" if not failed else "HARDENING_GAPS",
        "checks":checks,
        "failed_checks":failed,
        "security_headers":"Applied by SecurityHeadersMiddleware",
        "request_ids":"Enabled",
        "generated_at":datetime.now(timezone.utc).isoformat(),
    }
