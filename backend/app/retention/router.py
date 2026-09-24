"""Retention catalogue & erasure request APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.retention.service import (
    RetentionError,
    create_request,
    decide_request,
    list_requests,
    retention_catalogue,
)

router = APIRouter(prefix="/api/v1/retention", tags=["Retention"])


def _map(err: RetentionError) -> HTTPException:
    code = str(err)
    return HTTPException(status_code=404 if "NOT_FOUND" in code else 400, detail=code)


class CreateBody(BaseModel):
    person_id: UUID
    request_type: str = Field(default="ERASURE", max_length=40)
    reason: str | None = Field(default=None, max_length=2000)


class DecideBody(BaseModel):
    status: str
    decision_notes: str | None = Field(default=None, max_length=2000)
    apply_pseudonym: bool = False


@router.get("/policies")
def policies(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return retention_catalogue()


@router.post("/requests")
def create(
    body: CreateBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        req = create_request(
            db,
            person_id=body.person_id,
            request_type=body.request_type,
            reason=body.reason,
            facility_id=facility_id,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": str(req.id), "status": req.status, "request_type": req.request_type}
    except RetentionError as e:
        raise _map(e) from e


@router.get("/requests")
def list_req(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    status: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=50, ge=1, le=200),
):
    _ = user
    return {"requests": list_requests(db, facility_id=facility_id, status=status, limit=limit)}


@router.post("/requests/{request_id}/decide")
def decide(
    request_id: UUID,
    body: DecideBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = facility_id
    try:
        req = decide_request(
            db,
            request_id=request_id,
            status=body.status,
            decision_notes=body.decision_notes,
            actor_user_id=user.id,
            apply_pseudonym=body.apply_pseudonym,
            facility_id=facility_id,
        )
        db.commit()
        return {
            "id": str(req.id),
            "status": req.status,
            "fulfilled_at": req.fulfilled_at.isoformat() if req.fulfilled_at else None,
        }
    except RetentionError as e:
        raise _map(e) from e
