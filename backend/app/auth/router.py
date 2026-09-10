from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import FacilityOption, FacilitySelectionRequest, LoginRequest, TokenResponse
from app.auth.service import authenticate_user, issue_access_token
from app.config import settings
from app.database import get_db
from app.facilities.models import Facility, Staff
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    result = authenticate_user(db, payload.username, payload.password)
    if result is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_CREDENTIALS", headers={"WWW-Authenticate": "Bearer"})
    user, staff = result
    if len(staff) != 1:
        raise HTTPException(status_code=409, detail="FACILITY_SELECTION_REQUIRED")
    return TokenResponse(access_token=issue_access_token(user, staff[0].facility_id), expires_in=settings.access_token_minutes * 60)

@router.get("/facilities", response_model=list[FacilityOption])
def facilities(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[FacilityOption]:
    rows = db.execute(select(Facility.id, Facility.name).join(Staff, Staff.facility_id == Facility.id).where(Staff.person_id == user.person_id, Staff.status == "ACTIVE", Facility.status == "ACTIVE").distinct()).all()
    return [FacilityOption(facility_id=row[0], facility_name=row[1]) for row in rows]

@router.post("/select-facility", response_model=TokenResponse)
def select_facility(payload: FacilitySelectionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TokenResponse:
    staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == payload.facility_id, Staff.status == "ACTIVE"))
    facility = db.get(Facility, payload.facility_id)
    if staff is None or facility is None or facility.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return TokenResponse(access_token=issue_access_token(user, payload.facility_id), expires_in=settings.access_token_minutes * 60)

@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict[str, object]:
    return {"success": True, "data": {"user_id": str(user.id), "username": user.username, "status": user.status}, "message": "Authenticated user"}
