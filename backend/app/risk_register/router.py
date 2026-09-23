"""Residual risk register APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.rbac.models import User
from app.risk_register.service import RiskError, list_risks, posture, seed_defaults, update_risk

router = APIRouter(prefix="/api/v1/risk-register", tags=["RiskRegister"])


def _map(err: RiskError) -> HTTPException:
    code = str(err)
    return HTTPException(status_code=404 if "NOT_FOUND" in code else 400, detail=code)


class UpdateBody(BaseModel):
    status: str | None = Field(default=None, max_length=30)
    residual_level: str | None = Field(default=None, max_length=20)
    treatment: str | None = Field(default=None, max_length=40)
    controls: str | None = Field(default=None, max_length=4000)
    owner: str | None = Field(default=None, max_length=120)


@router.post("/seed")
def seed(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    result = seed_defaults(db)
    db.commit()
    return result


@router.get("/posture")
def risk_posture(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    data = posture(db)
    db.commit()
    return data


@router.get("/risks")
def get_risks(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    status: str | None = Query(default=None, max_length=30),
    category: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=200),
):
    _ = user
    seed_defaults(db)
    db.commit()
    return {"risks": list_risks(db, status=status, category=category, limit=limit)}


@router.patch("/risks/{risk_id}")
def patch_risk(
    risk_id: UUID,
    body: UpdateBody,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        row = update_risk(
            db,
            risk_id=risk_id,
            status=body.status,
            residual_level=body.residual_level,
            treatment=body.treatment,
            controls=body.controls,
            owner=body.owner,
            actor_user_id=user.id,
        )
        db.commit()
        return {
            "id": str(row.id),
            "code": row.code,
            "status": row.status,
            "residual_level": row.residual_level,
        }
    except RiskError as e:
        raise _map(e) from e
