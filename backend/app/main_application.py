"""AfyaSync API application bootstrap (Phase 140).

Mounts routers from router_registry so the API is fully usable after main.py
recovery. Developed by BAHATI GAD WANGWE.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

logger = logging.getLogger("afyasync")

try:
    from app.config import settings
except Exception:  # pragma: no cover

    class _S:
        app_name = "AfyaSync API"
        app_version = "0.0.0"
        environment = "development"
        cors_origins = ["*"]

    settings = _S()  # type: ignore

app = FastAPI(
    title=getattr(settings, "app_name", "AfyaSync API"),
    version=getattr(settings, "app_version", "0.0.0"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "cors_origins", ["*"]) or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_mounted: list[str] = []
_failed: list[str] = []


def _mount_routers() -> None:
    try:
        from app.router_registry import ROUTERS
    except Exception:
        ROUTERS = [
            ("app.clinical.router", "router", "clinical_router"),
            ("app.clinical.worklist_routes", "worklist_router", "worklist_router"),
            ("app.encounters.router", "router", "encounters_router"),
            ("app.auth", "router", "auth_router"),
        ]
    for mod_name, attr, label in ROUTERS:
        try:
            mod = __import__(mod_name, fromlist=[attr])
            router = getattr(mod, attr)
            app.include_router(router)
            _mounted.append(label)
            logger.info("mounted_%s", label)
        except Exception:
            _failed.append(label)
            logger.exception("failed_to_mount_%s", label)


_mount_routers()


@app.on_event("startup")
def _startup() -> None:
    try:
        from app.clinical.startup_check import run_clinical_startup_checks

        run_clinical_startup_checks()
    except Exception:
        logger.exception("Clinical startup check failed")


@app.get("/health", tags=["System"])
def health():
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "service": "afasync-api",
            "routers_mounted": len(_mounted),
            "routers_failed": len(_failed),
        },
        "message": "AfyaSync API is running",
    }


@app.get("/ready", tags=["System"])
def ready(response: Response):
    clinical_departments = {"status": "unknown"}
    try:
        from app.clinical.path_hardening import assert_department_services_loaded

        clinical_departments = {
            "status": "ok",
            "modules": assert_department_services_loaded(),
        }
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
                "bootstrap": "main_application",
                "routers_mounted": _mounted[:50],
                "routers_failed": _failed[:20],
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
                "routers_failed": _failed[:20],
            },
            "message": "AfyaSync API is not ready",
        }
