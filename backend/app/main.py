from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AfyaSync healthcare platform API",
)


@app.get("/health", tags=["System"])
def health_check() -> dict[str, object]:
    return {
        "success": True,
        "data": {"status": "ok", "environment": settings.environment},
        "message": "AfyaSync API is running",
    }


@app.get("/api/v1", tags=["System"])
def api_root() -> dict[str, object]:
    return {
        "success": True,
        "data": {"name": settings.app_name, "version": settings.app_version},
        "message": "AfyaSync API v1",
    }
