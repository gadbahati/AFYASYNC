from fastapi import APIRouter, Depends

from app.auth.dependencies import require_national_permission
from app.operations.service import system_snapshot
from app.rbac.models import User
from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/operations", tags=["Operations"])


@router.get("/command-centre")
def command_centre(user: User = Depends(require_national_permission("operations.observability.read")), db: Session = Depends(get_db)) -> dict:
    return {"success": True, "data": system_snapshot(db), "message": "AfyaSync command centre snapshot"}
