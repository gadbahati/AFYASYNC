from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.coverage.schemas import CoverageCreate, CoverageResponse
from app.coverage.service import create_coverage, get_active_coverage
from app.database import get_db

router = APIRouter(prefix="/api/v1/coverage", tags=["Coverage"])


@router.post("", response_model=CoverageResponse, status_code=status.HTTP_201_CREATED)
def add_coverage(payload: CoverageCreate, db: Session = Depends(get_db)) -> CoverageResponse:
    try:
        coverage = create_coverage(db, payload)
    except ValueError as exc:
        code = str(exc)
        messages = {
            "INVALID_COVERAGE_DATES": "Coverage end date cannot be before start date.",
            "PAYER_NOT_FOUND": "The selected payer is not available.",
            "INVALID_PAYER_PLAN": "The selected payer plan is invalid.",
        }
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": messages[code]}) from exc
    return coverage


@router.get("/person/{person_id}/active", response_model=list[CoverageResponse])
def active_coverage(person_id: UUID, db: Session = Depends(get_db)) -> list[CoverageResponse]:
    return get_active_coverage(db, person_id)
