"""Performance, reliability & chaos readiness APIs."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.rbac.models import User
from app.reliability.service import (
    chaos_drill_catalog,
    dependency_probes,
    performance_snapshot,
    readiness_matrix,
)

router = APIRouter(prefix="/api/v1/reliability", tags=["Reliability"])


@router.get("/probes")
def probes(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return dependency_probes(db)


@router.get("/performance")
def performance(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return performance_snapshot()


@router.get("/readiness-matrix")
def matrix(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return readiness_matrix(db)


@router.get("/chaos-catalog")
def chaos(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return chaos_drill_catalog()
