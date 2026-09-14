from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_national_permission
from app.database import get_db
from app.national_capacity.schemas import NationalCapacityResponse
from app.national_capacity.service import get_national_capacity
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/national/capacity", tags=["National Capacity"])


@router.get("/overview", response_model=NationalCapacityResponse)
def national_capacity_overview(
    county: str | None = Query(default=None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission("reports.national.read")),
) -> NationalCapacityResponse:
    return get_national_capacity(db, actor_user_id=user.id, county=county)
