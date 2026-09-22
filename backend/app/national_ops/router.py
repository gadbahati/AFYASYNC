"""National program readiness APIs."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.national_ops.readiness import NATIONAL_API_CATALOGUE, national_readiness

router = APIRouter(prefix="/api/v1/national", tags=["National Program"])


@router.get("/readiness")
def readiness(db: Session = Depends(get_db)):
    """Import + schema readiness for national phases 0–10."""
    return national_readiness(db)


@router.get("/api-catalogue")
def api_catalogue():
    """Public catalogue of national differentiation APIs."""
    return {
        "developer": "BAHATI GAD WANGWE",
        "phases": "0-10",
        "count": len(NATIONAL_API_CATALOGUE),
        "apis": NATIONAL_API_CATALOGUE,
    }
