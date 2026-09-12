from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from sqlalchemy import text

from app.admissions import models as admission_models
from app.admissions.router import router as admissions_router
from app.appointments import models as appointment_models
from app.appointments.router import router as appointments_router
from app.audit import models as audit_models
from app.auth import models as auth_models
from app.auth import router as auth_router
from app.benefits import models as benefit_models
from app.benefits.router import router as benefits_router
from app.billing import models as billing_models
from app.billing.router import router as billing_router
from app.bootstrap import ensure_demo_admin
from app.claims import models as claims_models
from app.claims.router import router as claims_router
from app.clinical import models as clinical_models
from app.clinical.router import router as clinical_router
from app.config import settings
from app.coverage import models as coverage_models
from app.coverage.router import router as coverage_router
from app.database import Base, SessionLocal, engine
from app.encounters import models as encounter_models
from app.encounters.router import router as encounters_router
from app.facilities import models as facility_models
from app.facilities.router import router as facilities_router
from app.integrations import models as integration_models
from app.integrations.router import router as integrations_router
from app.laboratory import models as laboratory_models
from app.laboratory.router import router as laboratory_router
from app.notifications import models as notification_models
from app.notifications.router import router as notifications_router
from app.patients import models as patient_models
from app.patients.router import router as patients_router
from app.pharmacy import models as pharmacy_models
from app.pharmacy.router import router as pharmacy_router
from app.portal.router import router as portal_router
from app.preauthorizations import models as preauthorization_models
from app.preauthorizations.router import router as preauthorizations_router
from app.rbac import models as rbac_models
from app.referrals import models as referral_models
from app.referrals.router import router as referrals_router
from app.reports.router import router as reports_router

_ = (patient_models, coverage_models, facility_models, rbac_models, appointment_models,
     encounter_models, clinical_models, laboratory_models, pharmacy_models, billing_models,
     claims_models, integration_models, audit_models, referral_models, notification_models,
     auth_models, benefit_models, admission_models, preauthorization_models)

app = FastAPI(title=settings.app_name, version=settings.app_version, description="AfyaSync healthcare platform API")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        if settings.environment == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


_cors_origins = settings.cors_origin_list()
if _cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=_cors_origins, allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                       allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-AfyaSync-Timestamp", "X-AfyaSync-Signature"])
app.add_middleware(SecurityHeadersMiddleware)


@app.on_event("startup")
def initialize_database() -> None:
    if settings.environment != "production":
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            try:
                ensure_demo_admin(db)
            except Exception:
                db.rollback()


app.include_router(auth_router.router)
app.include_router(patients_router)
app.include_router(coverage_router)
app.include_router(benefits_router)
app.include_router(admissions_router)
app.include_router(preauthorizations_router)
app.include_router(facilities_router)
app.include_router(appointments_router)
app.include_router(encounters_router)
app.include_router(clinical_router)
app.include_router(laboratory_router)
app.include_router(pharmacy_router)
app.include_router(billing_router)
app.include_router(claims_router)
app.include_router(integrations_router)
app.include_router(referrals_router)
app.include_router(notifications_router)
app.include_router(portal_router)
app.include_router(reports_router)


@app.get("/health", tags=["System"])
def health_check() -> dict[str, object]:
    return {"success": True, "data": {"service": "afasync-api", "status": "healthy", "environment": settings.environment, "version": settings.app_version}, "message": "AfyaSync API is running"}


@app.get("/ready", tags=["System"])
def readiness_check(response: Response) -> dict[str, object]:
    db_ok = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"success": False, "data": {"service": "afasync-api", "status": "not_ready", "database": "unavailable"}, "message": "AfyaSync API is not ready"}
    return {"success": True, "data": {"service": "afasync-api", "status": "ready", "database": "ok"}, "message": "AfyaSync API is ready"}


@app.get("/api/v1", tags=["System"])
def api_root() -> dict[str, object]:
    return {"success": True, "data": {"name": settings.app_name, "version": settings.app_version}, "message": "AfyaSync API v1"}
