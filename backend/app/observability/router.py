from fastapi import APIRouter, Depends
from app.auth.dependencies import require_national_permission
from app.rbac.models import User
from app.observability.service import runtime_metrics

router = APIRouter(prefix="/api/v1/observability", tags=["Observability"])

@router.get("/runtime")
def runtime_snapshot(user: User = Depends(require_national_permission("operations.observability.read"))):
    return {"success": True, "data": runtime_metrics.snapshot(), "message": "Runtime metrics"}
