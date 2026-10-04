from re import fullmatch
from uuid import uuid4
import logging

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# NOTE: This file is restored in Phase 139. If incomplete, see main.py history.
# Temporary minimal app so API boots while full module is restored.

logger = logging.getLogger("afyasync")

try:
    from app.config import settings
except Exception:
    class _S:
        app_name = "AfyaSync API"
        app_version = "0.0.0"
        environment = "development"
        cors_origins = ["*"]
    settings = _S()

app = FastAPI(title=getattr(settings, "app_name", "AfyaSync API"), version=getattr(settings, "app_version", "0.0.0"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "cors_origins", ["*"]) or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    try:
        from app.clinical.startup_check import run_clinical_startup_checks
        run_clinical_startup_checks()
    except Exception:
        logger.exception("Clinical startup check failed")
    try:
        from app.clinical.worklist_routes import worklist_router
        app.include_router(worklist_router)
    except Exception:
        logger.exception("Worklist router not mounted")


@app.get("/health")
def health():
    return {"success": True, "data": {"status": "healthy"}, "message": "AfyaSync API is running"}


@app.get("/ready")
def ready(response: Response):
    clinical_departments = {"status": "unknown"}
    try:
        from app.clinical.path_hardening import assert_department_services_loaded
        clinical_departments = {"status": "ok", "modules": assert_department_services_loaded()}
    except Exception as exc:
        clinical_departments = {"status": "degraded", "error": str(exc)[:200]}
    try:
        from app.database import SessionLocal
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {
            "success": True,
            "data": {
                "service": "afasync-api",
                "status": "ready",
                "clinical_departments": clinical_departments,
                "database": "ok",
            },
            "message": "AfyaSync API is ready",
        }
    except Exception:
        response.status_code = 503
        return {
            "success": False,
            "data": {
                "service": "afasync-api",
                "status": "not_ready",
                "clinical_departments": clinical_departments,
                "database": "unavailable",
            },
            "message": "AfyaSync API is not ready",
        }
