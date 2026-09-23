"""Performance acceptance APIs."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_permission
from app.performance.service import evaluate_acceptance, performance_catalogue
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/performance", tags=["Performance"])


@router.get("/catalogue")
def catalogue(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return performance_catalogue()


@router.get("/acceptance")
def acceptance(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return evaluate_acceptance()
