from fastapi import FastAPI

from app.appointments import models as appointment_models
from app.appointments.router import router as appointments_router
from app.audit import models as audit_models
from app.auth import router as auth_router
from app.billing import models as billing_models
from app.billing.router import router as billing_router
from app.claims import models as claims_models
from app.claims.router import router as claims_router
from app.clinical import models as clinical_models
from app.clinical.router import router as clinical_router
from app.config import settings
from app.coverage import models as coverage_models
from app.coverage.router import router as coverage_router
from app.database import Base, engine
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
from app.rbac import models as rbac_models
from app.referrals import models as referral_models
from app.referrals.router import router as referrals_router

_ = (patient_models, coverage_models, facility_models, rbac_models, appointment_models,
     encounter_models, clinical_models, laboratory_models, pharmacy_models, billing_models,
     claims_models, integration_models, audit_models, referral_models, notification_models)

app = FastAPI(title=settings.app_name, version=settings.app_version, description="AfyaSync healthcare platform API")


@app.on_event("startup")
def initialize_database() -> None:
    if settings.environment != "production":
        Base.metadata.create_all(bind=engine)


app.include_router(auth_router.router)
app.include_router(patients_router)
app.include_router(coverage_router)
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


@app.get("/health", tags=["System"])
def health_check() -> dict[str, object]:
    return {"success": True, "data": {"service": "afasync-api", "status": "healthy"}, "message": "AfyaSync API is running"}


@app.get("/api/v1", tags=["System"])
def api_root() -> dict[str, object]:
    return {"success": True, "data": {"name": settings.app_name, "version": settings.app_version}, "message": "AfyaSync API v1"}
