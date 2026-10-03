from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.national_audit.service import audit
from app.rbac.models import User

router=APIRouter(prefix="/api/v1/national-audit",tags=["NationalAudit"])

@router.get("")
def run_audit(db:Session=Depends(get_db), user:User=Depends(require_permission("reports.read"))):
    _=user
    return audit(db)
