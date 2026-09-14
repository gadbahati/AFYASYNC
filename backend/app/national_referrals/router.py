from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_national_permission
from app.database import get_db
from app.national_referrals.schemas import NationalReferralResponse
from app.national_referrals.service import get_national_referrals
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/national/referrals", tags=["National Referrals"])
REFERRAL_NETWORK_READ = "referral.network.read"
_ALLOWED_STATUSES = {"CREATED", "SENT", "ACCEPTED", "IN_PROGRESS", "COMPLETED", "DECLINED", "CANCELLED"}
_ALLOWED_PRIORITIES = {"ROUTINE", "URGENT", "EMERGENCY"}


@router.get("/overview", response_model=NationalReferralResponse)
def national_referral_overview(
    county: str | None = Query(default=None, min_length=1, max_length=100),
    status: str | None = Query(default=None, min_length=1, max_length=30),
    priority: str | None = Query(default=None, min_length=1, max_length=20),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=10000),
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission(REFERRAL_NETWORK_READ)),
) -> NationalReferralResponse:
    status_value = status.strip().upper() if status else None
    priority_value = priority.strip().upper() if priority else None
    if status_value and status_value not in _ALLOWED_STATUSES:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="INVALID_REFERRAL_STATUS_FILTER")
    if priority_value and priority_value not in _ALLOWED_PRIORITIES:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="INVALID_REFERRAL_PRIORITY_FILTER")
    if start_date and end_date and start_date > end_date:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="INVALID_REFERRAL_DATE_RANGE")
    return get_national_referrals(
        db,
        actor_user_id=user.id,
        county=county,
        status=status_value,
        priority=priority_value,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
