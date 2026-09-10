from fastapi import FastAPI

from app.config import settings
from app.coverage import models as coverage_models
from app.coverage.router import router as coverage_router
from app.database import Base, engine
from app.facilities import models as facility_models
from app.facilities.router import router as facilities_router
from app.patients import models as patient_models
from app.patients.router import router as patients_router

# Import models before metadata creation so SQLAlchemy knows all tables.
_ = patient_models, coverage_models, facility_models

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AfyaSync healthcare platform API",
)


@app.on_event("startup")
def initialize_database() -> None:
    """Create development tables when the API starts.

    Alembic migrations will become the source of truth before production.
    """
    if settings.environment != "production":
        Base.metadata.create_all(bind=engine)


app.include_router(patients_router)
app.include_router(coverage_router)
app.include_router(facilities_router)


@app.get("/health", tags=["System"])
def health_check() -> dict[str, object]:
    return {
        "success": True,
        "data": {"service": "afasync-api", "status": "healthy"},
        "message": "AfyaSync API is running",
    }


@app.get("/api/v1", tags=["System"])
def api_root() -> dict[str, object]:
    return {
        "success": True,
        "data": {"name": settings.app_name, "version": settings.app_version},
        "message": "AfyaSync API v1",
    }
