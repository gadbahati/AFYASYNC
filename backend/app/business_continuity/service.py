from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.business_continuity.models import BusinessContinuityEvent, BusinessContinuityPlan
from app.rbac.models import User
from app.tenancy.service import accessible_organizations, get_accessible_organization


def overview(db: Session, user: User) -> dict:
    orgs = accessible_organizations(db, user)
    org_ids = [o.id for o in orgs]
    plans = list(db.scalars(
        select(BusinessContinuityPlan)
        .where(BusinessContinuityPlan.organization_id.in_(org_ids))
        .order_by(BusinessContinuityPlan.updated_at.desc())
    ).all()) if org_ids else []
    now = datetime.now(timezone.utc)
    stale = [
        p for p in plans
        if not p.last_tested_at or (now - p.last_tested_at).days > 90
    ]
    return {
        "organizations": len(orgs),
        "plans": len(plans),
        "tested_within_90_days": len(plans) - len(stale),
        "stale_or_never_tested": len(stale),
        "plans": [
            {
                "id": str(p.id),
                "organization_id": str(p.organization_id),
                "service_tier": p.service_tier,
                "rto_minutes": p.rto_minutes,
                "rpo_minutes": p.rpo_minutes,
                "offline_max_hours": p.offline_max_hours,
                "backup_cadence_minutes": p.backup_cadence_minutes,
                "status": p.status,
                "last_tested_at": p.last_tested_at.isoformat() if p.last_tested_at else None,
            } for p in plans
        ],
        "control": "Tenant-scoped continuity posture; detailed restore evidence remains in /api/v1/dr.",
    }


def create_plan(db: Session, *, user: User, organization_id: UUID, rto_minutes: int, rpo_minutes: int, offline_max_hours: int, backup_cadence_minutes: int, notes: str | None) -> BusinessContinuityPlan:
    get_accessible_organization(db, user=user, organization_id=organization_id)
    row = BusinessContinuityPlan(
        organization_id=organization_id,
        rto_minutes=rto_minutes,
        rpo_minutes=rpo_minutes,
        offline_max_hours=offline_max_hours,
        backup_cadence_minutes=backup_cadence_minutes,
        status="ACTIVE",
        owner_user_id=user.id,
        notes=(notes or "").strip()[:4000] or None,
    )
    db.add(row); db.flush()
    record_audit(db, action="BCP_CREATED", resource_type="BUSINESS_CONTINUITY_PLAN", resource_id=str(row.id), result="SUCCESS", user_id=user.id, metadata={"organization_id": str(organization_id)}, commit=False)
    return row


def record_test(db: Session, *, user: User, plan_id: UUID, result: str, measured_rto_minutes: int | None, measured_rpo_minutes: int | None, notes: str | None) -> BusinessContinuityEvent:
    plan = db.get(BusinessContinuityPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="BCP_NOT_FOUND")
    get_accessible_organization(db, user=user, organization_id=plan.organization_id)
    result = result.strip().upper()
    if result not in {"PASS", "FAIL", "PARTIAL"}:
        raise HTTPException(status_code=400, detail="INVALID_BCP_TEST_RESULT")
    event = BusinessContinuityEvent(
        plan_id=plan.id,
        event_type="RECOVERY_TEST",
        result=result,
        measured_rto_minutes=measured_rto_minutes,
        measured_rpo_minutes=measured_rpo_minutes,
        notes=(notes or "").strip()[:4000] or None,
        actor_user_id=user.id,
    )
    db.add(event)
    plan.last_tested_at = datetime.now(timezone.utc)
    plan.status = "ACTIVE" if result == "PASS" else "REVIEW"
    db.flush()
    record_audit(db, action="BCP_TEST_RECORDED", resource_type="BUSINESS_CONTINUITY_PLAN", resource_id=str(plan.id), result=result, user_id=user.id, metadata={"measured_rto_minutes": measured_rto_minutes, "measured_rpo_minutes": measured_rpo_minutes}, commit=False)
    return event
