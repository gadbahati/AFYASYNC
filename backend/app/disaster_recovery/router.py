"""Disaster recovery drills & backup verification APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.disaster_recovery.service import (
    DRError,
    complete_drill,
    dr_checklist,
    list_backups,
    list_drills,
    posture,
    record_backup,
    start_drill,
)
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/dr", tags=["DisasterRecovery"])


def _map(err: DRError) -> HTTPException:
    code = str(err)
    return HTTPException(status_code=404 if "NOT_FOUND" in code else 400, detail=code)


class BackupBody(BaseModel):
    source: str = Field(default="POSTGRES", max_length=80)
    status: str = Field(default="RECORDED", max_length=30)
    detail: str | None = Field(default=None, max_length=2000)


class DrillStartBody(BaseModel):
    drill_type: str = Field(default="TABLETOP", max_length=40)
    scenario: str = Field(min_length=5, max_length=500)
    rto_minutes_target: int | None = Field(default=None, ge=1, le=10080)
    rpo_minutes_target: int | None = Field(default=None, ge=0, le=10080)


class DrillCompleteBody(BaseModel):
    status: str = Field(max_length=30)
    outcome_notes: str | None = Field(default=None, max_length=2000)


@router.get("/checklist")
def checklist(user: User = Depends(require_permission("reports.read"))):
    _ = user
    return dr_checklist()


@router.get("/posture")
def dr_posture(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return posture(db)


@router.post("/backups")
def post_backup(
    body: BackupBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        row = record_backup(
            db,
            source=body.source,
            status=body.status,
            detail=body.detail,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(row.id), "source": row.source, "status": row.status}
    except DRError as e:
        raise _map(e) from e


@router.get("/backups")
def get_backups(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    limit: int = Query(default=20, ge=1, le=100),
):
    _ = user
    return {"backups": list_backups(db, limit=limit)}


@router.post("/drills")
def post_drill(
    body: DrillStartBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        row = start_drill(
            db,
            drill_type=body.drill_type,
            scenario=body.scenario,
            rto_minutes_target=body.rto_minutes_target,
            rpo_minutes_target=body.rpo_minutes_target,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(row.id), "status": row.status, "drill_type": row.drill_type}
    except DRError as e:
        raise _map(e) from e


@router.post("/drills/{drill_id}/complete")
def finish_drill(
    drill_id: UUID,
    body: DrillCompleteBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        row = complete_drill(
            db,
            drill_id=drill_id,
            status=body.status,
            outcome_notes=body.outcome_notes,
            actor_user_id=user.id,
        )
        db.commit()
        return {
            "id": str(row.id),
            "status": row.status,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
        }
    except DRError as e:
        raise _map(e) from e


@router.get("/drills")
def get_drills(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    limit: int = Query(default=20, ge=1, le=100),
):
    _ = user
    return {"drills": list_drills(db, limit=limit)}
