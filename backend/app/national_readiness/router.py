"""Final national readiness declaration API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.national_readiness.service import declaration
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/national-readiness", tags=["NationalReadiness"])


@router.get("/declaration")
def national_declaration(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    data = declaration(db)
    try:
        db.commit()
    except Exception:
        db.rollback()
    return data
