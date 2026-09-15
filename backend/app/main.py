from re import fullmatch
from uuid import uuid4

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
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
from app.claims import models as claims_models
from app.claims.router import router as claims_router
from app.claims.preflight_router import router as claim_preflight_router
from app.clinical import models as clinical_models
from app.clinical.router import router as clinical_router
from app.config import settings
from app.coverage import models as coverage_models
from app.coverage.router import router as coverage_router
from app.coverage.sha_eligibility_router import router as sha_eligibility_router
from app.coverage.payer_admin_router import router as payer_network_router
from app.database import Base, SessionLocal, engine
from app.emergency import models as emergency_models
from app.emergency.router import router as emergency_router
from app.encounters import models as encounter_models
from app.encounters.router import router as encounters_router
from app.facilities import models as facility_models
from app.facilities.router import router as facilities_router
from app.insight.router import router as insight_router
from app.integrations import models as integration_models
from app.integrations.router import router as integrations_router
from app.interoperability.router import router as interoperability_router
from app.laboratory import models as laboratory_models
from app.laboratory.router import router as laboratory_router
from app.maternity import models as maternity_models
from app.maternity.router import router as maternity_router
from app.child_health import models as child_health_models
from app.child_health.router import router as child_health_router
from app.blood_bank import models as blood_bank_models
from app.blood_bank.router import router as blood_bank_router
from app.patient_safety import models as patient_safety_models
from app.patient_safety.router import router as patient_safety_router
from app.dietetics import models as dietetics_models
from app.dietetics.router import router as dietetics_router
from app.infection_control import models as infection_control_models
from app.infection_control.router import router as infection_control_router
from app.notifications import models as notification_models
from app.notifications.router import router as notifications_router
from app.nursing import models as nursing_models
from app.nursing.router import router as nursing_router
from app.national_capacity.router import router as national_capacity_router
from app.national_supply.router import router as national_supply_router
from app.national_supply.planning_router import router as national_supply_planning_router
from app.national_referrals.router import router as national_referrals_router
from app.observability.router import router as observability_router
from app.observability.service import runtime_metrics
from app.patients import models as patient_models
from app.patients.national_identity_router import router as national_identity_router
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
from app.theatre import models as theatre_models
from app.theatre.router import router as theatre_router
from app.radiology import models as radiology_models
from app.radiology.router import router as radiology_router
from app.wards import models as ward_models
from app.wards.router import router as wards_router
from app.wards.movement_router import router as ward_movement_router
from app.ussd.router import router as ussd_router

app = FastAPI(title=settings.app_name, version=settings.app_version)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    @staticmethod
    def _request_id(request: Request) -> str:
        supplied = request.headers.get("X-Request-ID", "").strip()
        if supplied and len(supplied) <= 128 and fullmatch(r"[A-Za-z0-9._:-]+", supplied):
            return supplied
        return str(uuid4())

    @staticmethod
    def _apply_headers(response, request_id: str) -> None:
        response.headers["X-Request-ID"] = request_id
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        response.headers.setdefault("Cache-Control", "no-store")
        if settings.environment == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    async def dispatch(self, request: Request, call_next):
        request_id = self._request_id(request)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception:
            runtime_metrics.request(error=True)
            response = JSONResponse(status_code=500, content={"success": False, "data": {"request_id": request_id}, "message": "Internal server error"})
            self._apply_headers(response, request_id)
            return response
        runtime_metrics.request(error=response.status_code >= 500)
        self._apply_headers(response, request_id)
        return response


_cors_origins = settings.cors_origin_list()
if _cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=_cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-AfyaSync-Timestamp", "X-AfyaSync-Signature", "X-Request-ID"])
app.add_middleware(SecurityHeadersMiddleware)


@app.on_event("startup")
def initialize_database():
    if settings.environment != "production":
        Base.metadata.create_all(bind=engine)
    import os
    seed_requested = os.getenv("SEED_UNIVERSAL_ADMIN", "").strip().lower() in {"1", "true", "yes"}
    bootstrap_requested = os.getenv("BOOTSTRAP_UNIVERSAL_ADMIN_ONCE", "").strip().lower() in {"1", "true", "yes"}
    if seed_requested and settings.environment == "production" and not bootstrap_requested:
        raise RuntimeError("SEED_UNIVERSAL_ADMIN is forbidden in production")
    if seed_requested or bootstrap_requested:
        from app.scripts.seed_universal_admin import seed_universal_admin
        result = seed_universal_admin()
        print("UNIVERSAL_ADMIN_BOOTSTRAP:", result)


app.include_router(auth_router.router)
app.include_router(patients_router)
app.include_router(national_identity_router)
app.include_router(coverage_router)
app.include_router(sha_eligibility_router)
app.include_router(payer_network_router)
app.include_router(benefits_router)
app.include_router(admissions_router)
app.include_router(preauthorizations_router)
app.include_router(emergency_router)
app.include_router(nursing_router)
app.include_router(wards_router)
app.include_router(ward_movement_router)
app.include_router(radiology_router)
app.include_router(theatre_router)
app.include_router(maternity_router)
app.include_router(child_health_router)
app.include_router(blood_bank_router)
app.include_router(patient_safety_router)
app.include_router(dietetics_router)
app.include_router(infection_control_router)
app.include_router(facilities_router)
app.include_router(appointments_router)
app.include_router(encounters_router)
app.include_router(clinical_router)
app.include_router(laboratory_router)
app.include_router(pharmacy_router)
app.include_router(billing_router)
app.include_router(claims_router)
app.include_router(claim_preflight_router)
app.include_router(integrations_router)
app.include_router(referrals_router)
app.include_router(notifications_router)
app.include_router(portal_router)
app.include_router(reports_router)
app.include_router(insight_router)
app.include_router(interoperability_router)
app.include_router(national_supply_router)
app.include_router(national_supply_planning_router)
app.include_router(national_referrals_router)
app.include_router(national_capacity_router)
app.include_router(observability_router)
app.include_router(ussd_router)


@app.get("/health", tags=["System"])
def health_check():
    return {"success": True, "data": {"service": "afasync-api", "status": "healthy", "environment": settings.environment, "version": settings.app_version}, "message": "AfyaSync API is running"}


@app.get("/ready", tags=["System"])
def readiness_check(response: Response):
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"success": True, "data": {"service": "afasync-api", "status": "ready", "database": "ok"}, "message": "AfyaSync API is ready"}
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"success": False, "data": {"service": "afasync-api", "status": "not_ready", "database": "unavailable"}, "message": "AfyaSync API is not ready"}


@app.get("/api/v1", tags=["System"])
def api_root():
    return {"success": True, "data": {"name": settings.app_name, "version": settings.app_version}, "message": "AfyaSync API v1"}
