from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.benefits.schemas import BenefitPackageResponse
from app.benefits.service import list_active_benefit_packages
from app.coverage.permissions import COVERAGE_READ
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/benefits", tags=["Benefits"])


@router.get("/packages", response_model=list[BenefitPackageResponse])
def list_benefit_packages(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(COVERAGE_READ)),
) -> list[BenefitPackageResponse]:
    return list_active_benefit_packages(db, facility_id=facility_id, actor_user_id=user.id)
