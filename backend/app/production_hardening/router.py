from fastapi import APIRouter, Depends

from app.auth.dependencies import require_permission
from app.production_hardening.service import hardening_manifest
from app.rbac.models import User

router=APIRouter(prefix="/api/v1/production-hardening",tags=["ProductionHardening"])

@router.get("")
def manifest(user:User=Depends(require_permission("reports.read"))):
    _=user
    return hardening_manifest()
