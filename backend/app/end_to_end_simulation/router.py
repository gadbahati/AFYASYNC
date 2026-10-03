from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.rbac.models import User
from app.end_to_end_simulation.service import run_simulation

router=APIRouter(prefix="/api/v1/end-to-end-simulation",tags=["EndToEndSimulation"])

@router.post("/run")
def simulate(db:Session=Depends(get_db), user:User=Depends(require_permission("reports.read"))):
    _=user
    return run_simulation(db)
