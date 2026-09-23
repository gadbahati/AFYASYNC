"""Observability APIs — runtime metrics, SLOs, tracing hooks."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_permission
from app.observability.service import evaluate_slos, runtime_metrics, tracing_hooks
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/observability", tags=["Observability"])


@router.get("/runtime")
def runtime_snapshot(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return {
        "success": True,
        "data": runtime_metrics.snapshot(),
        "message": "Runtime metrics",
        "developer": "BAHATI GAD WANGWE",
    }


@router.get("/slos")
def slos(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return evaluate_slos()


@router.get("/tracing-hooks")
def hooks(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return tracing_hooks()
