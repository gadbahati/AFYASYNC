"""Change-control and release governance APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.change_control.service import (
    ChangeError,
    create_change,
    governance_policy,
    list_changes,
    list_releases,
    record_release,
    transition_change,
)
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/change-control", tags=["ChangeControl"])


def _map(err: ChangeError) -> HTTPException:
    code = str(err)
    return HTTPException(status_code=404 if "NOT_FOUND" in code else 400, detail=code)


class ChangeBody(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=5000)
    change_type: str = Field(default="STANDARD", max_length=40)
    risk_level: str = Field(default="MEDIUM", max_length=20)


class TransitionBody(BaseModel):
    status: str = Field(max_length=30)
    decision_notes: str | None = Field(default=None, max_length=2000)


class ReleaseBody(BaseModel):
    version: str = Field(min_length=1, max_length=40)
    environment: str = Field(default="staging", max_length=30)
    status: str = Field(default="PLANNED", max_length=30)
    notes: str | None = Field(default=None, max_length=2000)
    change_request_id: UUID | None = None


@router.get("/policy")
def policy(user: User = Depends(require_permission("reports.read"))):
    _ = user
    return governance_policy()


@router.post("/changes")
def post_change(
    body: ChangeBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        row = create_change(
            db,
            title=body.title,
            description=body.description,
            change_type=body.change_type,
            risk_level=body.risk_level,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(row.id), "status": row.status}
    except ChangeError as e:
        raise _map(e) from e


@router.get("/changes")
def get_changes(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    status: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=50, ge=1, le=200),
):
    _ = user
    return {"changes": list_changes(db, status=status, limit=limit)}


@router.post("/changes/{change_id}/transition")
def post_transition(
    change_id: UUID,
    body: TransitionBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        row = transition_change(
            db,
            change_id=change_id,
            status=body.status,
            decision_notes=body.decision_notes,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(row.id), "status": row.status}
    except ChangeError as e:
        raise _map(e) from e


@router.post("/releases")
def post_release(
    body: ReleaseBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        row = record_release(
            db,
            version=body.version,
            environment=body.environment,
            status=body.status,
            notes=body.notes,
            change_request_id=body.change_request_id,
            actor_user_id=user.id,
        )
        db.commit()
        return {
            "id": str(row.id),
            "version": row.version,
            "environment": row.environment,
            "status": row.status,
        }
    except ChangeError as e:
        raise _map(e) from e


@router.get("/releases")
def get_releases(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    limit: int = Query(default=30, ge=1, le=100),
):
    _ = user
    return {"releases": list_releases(db, limit=limit)}
