"""Hospital OS facility APIs — journey + integrity."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.hospital_os.journey_service import get_encounter_journey, scan_facility_orphans
from app.hospital_os.schemas import EncounterJourney, FacilityIntegrityReport
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/hospital-os", tags=["Hospital OS"])

ENCOUNTER_READ = "encounters.read"
REPORT_READ = "reports.read"


@router.get("/encounters/{encounter_id}/journey", response_model=EncounterJourney)
def encounter_journey(
    encounter_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(ENCOUNTER_READ)),
) -> EncounterJourney:
    try:
        return get_encounter_journey(db, encounter_id, facility_id)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=404 if code == "ENCOUNTER_NOT_FOUND" else 400,
            detail={"code": code, "message": code},
        ) from exc


@router.get("/integrity", response_model=FacilityIntegrityReport)
def facility_integrity(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(REPORT_READ)),
) -> FacilityIntegrityReport:
    report = scan_facility_orphans(db, facility_id, limit=limit)
    db.commit()
    return report
