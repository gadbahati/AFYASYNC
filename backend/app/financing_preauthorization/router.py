from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.financing_preauthorization.schemas import (
    FinancingPreauthDecision,
    FinancingPreauthRequest,
    FinancingPreauthResponse,
)
from app.financing_preauthorization.service import (
    FinancingPreauthError,
    decide,
    list_for_facility,
    request,
)
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/financing-preauthorizations", tags=["Financing preauthorizations"])


@router.post("", response_model=FinancingPreauthResponse, status_code=201)
def create(
    payload: FinancingPreauthRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("encounters.create")),
):
    try:
        return request(db, facility_id=facility_id, actor_user_id=user.id, payload=payload)
    except FinancingPreauthError as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc), "message": str(exc)}) from exc


@router.get("", response_model=list[FinancingPreauthResponse])
def list_preauths(
    status: str | None = Query(default=None),
    person_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("encounters.create")),
):
    _ = user
    return list_for_facility(
        db, facility_id=facility_id, status=status, person_id=person_id, limit=limit
    )


@router.post("/{authorization_id}/decision", response_model=FinancingPreauthResponse)
def decision(
    authorization_id: UUID,
    payload: FinancingPreauthDecision,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("encounters.create")),
):
    try:
        return decide(
            db,
            authorization_id=authorization_id,
            facility_id=facility_id,
            actor_user_id=user.id,
            payload=payload,
        )
    except FinancingPreauthError as exc:
        raise HTTPException(status_code=409, detail={"code": str(exc), "message": str(exc)}) from exc
