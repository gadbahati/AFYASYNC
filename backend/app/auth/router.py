from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import LoginRequest, TokenResponse
from app.auth.service import authenticate_user, issue_access_token
from app.config import settings
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    result = authenticate_user(db, payload.username, payload.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_CREDENTIALS",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user, staff = result
    facility_id = staff[0].facility_id if len(staff) == 1 else None
    return TokenResponse(
        access_token=issue_access_token(user, facility_id),
        expires_in=settings.access_token_minutes * 60,
    )


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict[str, object]:
    return {
        "success": True,
        "data": {"user_id": str(user.id), "username": user.username, "status": user.status},
        "message": "Authenticated user",
    }
