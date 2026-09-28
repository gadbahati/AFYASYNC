from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.adjudication.schemas import AdjudicationRunRequest, AdjudicationResponse
from app.adjudication.service import AdjudicationError, adjudicate

router = APIRouter(prefix="/api/v1/adjudication", tags=["Claims adjudication"])

@router.post("/run", response_model=AdjudicationResponse)
def run_adjudication(
    payload: AdjudicationRunRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.validate")),
):
    try:
        return adjudicate(db, claim_id=payload.claim_id, facility_id=facility_id, actor_user_id=user.id, force=payload.force)
    except AdjudicationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
