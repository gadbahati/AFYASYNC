from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_national_permission
from app.database import get_db
from app.patients.national_identity_schemas import NationalIdentityResolution
from app.patients.national_identity_service import resolve_national_identity
from app.rbac.models import User

NATIONAL_IDENTITY_READ = "identity.national.read"

router = APIRouter(prefix="/api/v1/national/identity", tags=["National Identity"])


@router.get("/resolve", response_model=NationalIdentityResolution)
def resolve_identity(
    afya_id: str = Query(min_length=1, max_length=20),
    user: User = Depends(require_national_permission(NATIONAL_IDENTITY_READ)),
    db: Session = Depends(get_db),
) -> NationalIdentityResolution:
    identity = resolve_national_identity(db, afya_id, actor_user_id=user.id)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "AFYA_ID_NOT_FOUND", "message": "No AfyaSync identity matched the supplied Afya ID."},
        )
    return identity
