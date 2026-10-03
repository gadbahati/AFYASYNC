from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.business_continuity.models import BusinessContinuityPlan
from app.disaster_recovery.models import DisasterRecoveryDrill
from app.facilities.models import Facility
from app.tenancy.models import Organization
from app.rbac.models import User


def audit(db: Session) -> dict:
    active_facilities = int(db.scalar(select(func.count()).select_from(Facility).where(Facility.status == "ACTIVE")) or 0)
    tenants = int(db.scalar(select(func.count()).select_from(Organization).where(Organization.status == "ACTIVE")) or 0)
    plans = int(db.scalar(select(func.count()).select_from(BusinessContinuityPlan)) or 0)
    passed_drills = int(db.scalar(select(func.count()).select_from(DisasterRecoveryDrill).where(DisasterRecoveryDrill.status == "PASSED")) or 0)
    active_users = int(db.scalar(select(func.count()).select_from(User).where(User.status == "ACTIVE")) or 0)

    checks = [
        {"id":"TENANCY","name":"Explicit organization tenancy exists","pass":tenants > 0},
        {"id":"FACILITIES","name":"Active facility registry is populated","pass":active_facilities > 0},
        {"id":"CONTINUITY","name":"Continuity plans exist","pass":plans > 0},
        {"id":"DR","name":"At least one passed DR drill is recorded","pass":passed_drills > 0},
        {"id":"IDENTITY","name":"Active user identities exist","pass":active_users > 0},
    ]
    failed=[c["id"] for c in checks if not c["pass"]]
    return {
        "phase":121,
        "overall":"PASS" if not failed else "GAPS_FOUND",
        "checks":checks,
        "failed_checks":failed,
        "inventory":{"active_facilities":active_facilities,"active_tenants":tenants,"continuity_plans":plans,"passed_dr_drills":passed_drills,"active_users":active_users},
        "note":"Software evidence audit only; external certification, security testing and government operational approvals remain external gates.",
        "generated_at":datetime.now(timezone.utc).isoformat(),
    }
