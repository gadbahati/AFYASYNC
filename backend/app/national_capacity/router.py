from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_national_permission
from app.database import get_db
from app.national_capacity.schemas import NationalCapacityResponse
from app.national_capacity.service import get_national_capacity, search_service_capacity
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/national/capacity", tags=["National Capacity"])


@router.get("/overview", response_model=NationalCapacityResponse)
def national_capacity_overview(
    county: str | None = Query(default=None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission("reports.national.read")),
) -> NationalCapacityResponse:
    return get_national_capacity(db, actor_user_id=user.id, county=county)

@router.get("/services")
def national_service_capacity(
    day: str | None = Query(default=None, description="YYYY-MM-DD"),
    service_code: str | None = Query(default=None, max_length=80),
    network_code: str | None = Query(default=None, max_length=80),
    county: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission("reports.national.read")),
):
    from datetime import datetime, timezone
    try:
        target = datetime.fromisoformat(day).replace(tzinfo=timezone.utc) if day else datetime.now(timezone.utc)
    except ValueError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="INVALID_DAY") from exc
    return search_service_capacity(
        db,
        actor_user_id=user.id,
        service_code=service_code,
        network_code=network_code,
        county=county,
        day=target,
        limit=limit,
    )
