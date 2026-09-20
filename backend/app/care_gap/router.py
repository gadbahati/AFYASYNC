"""National / county care-gap intelligence endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_national_permission
from app.care_gap.schemas import CareGapOverview, CountyCareGap
from app.care_gap.service import build_care_gap_overview
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/national/care-gaps", tags=["Care Gap Intelligence"])


@router.get("/overview", response_model=CareGapOverview)
def care_gap_overview(
    window_days: int = Query(default=30, ge=7, le=90),
    county: str | None = Query(default=None, max_length=100),
    top_n: int = Query(default=15, ge=1, le=47),
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission("reports.national.read")),
) -> CareGapOverview:
    """Aggregate care-gap scores by county (no patient-level data)."""
    return build_care_gap_overview(
        db,
        actor_user_id=user.id,
        window_days=window_days,
        county=county,
        top_n=top_n,
    )


@router.get("/counties", response_model=list[CountyCareGap])
def care_gap_counties(
    window_days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission("reports.national.read")),
) -> list[CountyCareGap]:
    overview = build_care_gap_overview(
        db,
        actor_user_id=user.id,
        window_days=window_days,
        county=None,
        top_n=47,
    )
    return overview.top_gap_counties


@router.get("/counties/{county_name}", response_model=CountyCareGap)
def care_gap_one_county(
    county_name: str,
    window_days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission("reports.national.read")),
) -> CountyCareGap:
    overview = build_care_gap_overview(
        db,
        actor_user_id=user.id,
        window_days=window_days,
        county=county_name,
        top_n=1,
    )
    if not overview.top_gap_counties:
        return CountyCareGap(
            county=county_name.strip() or "UNASSIGNED",
            gap_score=0,
            signals=[],
        )
    return overview.top_gap_counties[0]
