from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.business_continuity.service import create_plan, overview, record_test
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/business-continuity", tags=["BusinessContinuity"])


class PlanBody(BaseModel):
    organization_id: UUID
    rto_minutes: int = Field(default=240, ge=1, le=10080)
    rpo_minutes: int = Field(default=60, ge=0, le=10080)
    offline_max_hours: int = Field(default=24, ge=1, le=720)
    backup_cadence_minutes: int = Field(default=1440, ge=5, le=10080)
    notes: str | None = Field(default=None, max_length=4000)


class TestBody(BaseModel):
    result: str = Field(min_length=4, max_length=20)
    measured_rto_minutes: int | None = Field(default=None, ge=0, le=10080)
    measured_rpo_minutes: int | None = Field(default=None, ge=0, le=10080)
    notes: str | None = Field(default=None, max_length=4000)


@router.get("")
def get_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return overview(db, user)


@router.post("/plans")
def post_plan(body: PlanBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = create_plan(db, user=user, organization_id=body.organization_id, rto_minutes=body.rto_minutes, rpo_minutes=body.rpo_minutes, offline_max_hours=body.offline_max_hours, backup_cadence_minutes=body.backup_cadence_minutes, notes=body.notes)
    db.commit()
    return {"id": str(row.id), "organization_id": str(row.organization_id), "status": row.status}


@router.post("/plans/{plan_id}/tests")
def post_test(plan_id: UUID, body: TestBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = record_test(db, user=user, plan_id=plan_id, result=body.result, measured_rto_minutes=body.measured_rto_minutes, measured_rpo_minutes=body.measured_rpo_minutes, notes=body.notes)
    db.commit()
    return {"id": str(row.id), "plan_id": str(row.plan_id), "result": row.result}
