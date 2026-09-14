from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_national_permission
from app.database import get_db
from app.national_supply.planning_schemas import SupplyPlanningResponse
from app.national_supply.planning_service import get_supply_planning
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/national/supply", tags=["National Supply"])
SUPPLY_PLAN = "supply.network.plan"


@router.get("/planning", response_model=SupplyPlanningResponse)
def national_supply_planning(
    county: str | None = Query(default=None, min_length=1, max_length=100),
    medication_code: str | None = Query(default=None, min_length=1, max_length=50),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission(SUPPLY_PLAN)),
) -> SupplyPlanningResponse:
    return get_supply_planning(
        db,
        actor_user_id=user.id,
        county=county,
        medication_code=medication_code,
        limit=limit,
    )
