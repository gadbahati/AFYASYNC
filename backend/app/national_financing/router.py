from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_national_permission
from app.database import get_db
from app.national_financing.service import financing_overview
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/national-financing", tags=["National Financing Exchange"])


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_national_permission("reports.read")),
):
    return financing_overview(db)
