from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.product_readiness.service import final_readiness
from app.rbac.models import User

router=APIRouter(prefix="/api/v1/product-readiness",tags=["ProductReadiness"])

@router.get("")
def readiness(db:Session=Depends(get_db), user:User=Depends(require_permission("reports.read"))):
    _=user
    return final_readiness(db)
