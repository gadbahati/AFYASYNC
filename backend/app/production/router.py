"""Production readiness & deploy checklist APIs."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_permission
from app.production.service import deploy_checklist, production_readiness
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/production", tags=["Production"])


@router.get("/readiness")
def readiness(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return production_readiness()


@router.get("/deploy-checklist")
def checklist(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return deploy_checklist()
