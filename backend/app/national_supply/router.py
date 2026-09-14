from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_national_permission
from app.database import get_db
from app.national_supply.schemas import NationalSupplyResponse
from app.national_supply.service import get_national_supply
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/national/supply", tags=["National Supply"])
SUPPLY_READ = "supply.network.read"


@router.get("/inventory", response_model=NationalSupplyResponse)
def national_supply_inventory(
    county: str | None = Query(default=None, min_length=1, max_length=100),
    medication_code: str | None = Query(default=None, min_length=1, max_length=50),
    low_stock_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=10000),
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission(SUPPLY_READ)),
) -> NationalSupplyResponse:
    return get_national_supply(
        db,
        actor_user_id=user.id,
        county=county,
        medication_code=medication_code,
        low_stock_only=low_stock_only,
        limit=limit,
        offset=offset,
    )
