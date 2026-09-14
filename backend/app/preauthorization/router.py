from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.preauthorization.permissions import PREAUTHORIZATION_CREATE
from app.preauthorization.schemas import PreauthorizationCreate, PreauthorizationResponse
from app.preauthorization.service import create_preauthorization
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/coverage/preauthorizations", tags=["Preauthorization"])


@router.post("", response_model=PreauthorizationResponse, status_code=status.HTTP_201_CREATED)
def create_preauth(
    payload: PreauthorizationCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(PREAUTHORIZATION_CREATE)),
) -> PreauthorizationResponse:
    try:
        return create_preauthorization(
            db,
            payload,
            facility_id=facility_id,
            actor_user_id=user.id,
        )
    except ValueError as exc:
        code = str(exc)
        status_code = 403 if code == "PATIENT_FACILITY_ACCESS_DENIED" else 404 if code == "PATIENT_NOT_FOUND" else 409 if code == "DUPLICATE_ACTIVE_PREAUTHORIZATION" else 400
        raise HTTPException(status_code=status_code, detail=code) from exc
