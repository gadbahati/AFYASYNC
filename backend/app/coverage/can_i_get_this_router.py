"""Can I Get This? API — national Phase 2."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.coverage.can_i_get_this_schemas import CanIGetThisRequest, CanIGetThisResponse
from app.coverage.can_i_get_this_service import can_i_get_this, post_utilisation
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/coverage", tags=["Can I Get This"])

COVERAGE_READ = "coverage.read"
COVERAGE_WRITE = "coverage.write"


class UtilisationPost(BaseModel):
    coverage_id: UUID
    person_id: UUID
    service_code: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0, le=Decimal("100000000"))
    reference: str | None = Field(default=None, max_length=120)


@router.post("/can-i-get-this", response_model=CanIGetThisResponse)
def can_i_get_this_endpoint(
    payload: CanIGetThisRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(COVERAGE_READ)),
) -> CanIGetThisResponse:
    try:
        result = can_i_get_this(
            db, payload, facility_id=facility_id, actor_user_id=user.id
        )
        db.commit()
        return result
    except ValueError as exc:
        code = str(exc)
        status = 404 if code in {"PERSON_NOT_FOUND"} else 409 if code in {"PERSON_DECEASED"} else 400
        raise HTTPException(status_code=status, detail={"code": code, "message": code}) from exc


@router.post("/utilisation", status_code=201)
def post_utilisation_endpoint(
    payload: UtilisationPost,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(COVERAGE_WRITE)),
):
    try:
        post_utilisation(
            db,
            coverage_id=payload.coverage_id,
            person_id=payload.person_id,
            service_code=payload.service_code,
            amount=payload.amount,
            actor_user_id=user.id,
            facility_id=facility_id,
            reference=payload.reference,
        )
        db.commit()
        return {"status": "POSTED", "service_code": payload.service_code}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": str(exc), "message": str(exc)}) from exc
