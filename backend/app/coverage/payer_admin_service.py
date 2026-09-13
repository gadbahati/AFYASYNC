from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.coverage.models import Payer, PayerPlan
from app.coverage.payer_admin_schemas import PayerCreate, PayerPlanCreate, PayerPlanUpdate, PayerUpdate


PAYER_TRANSITIONS = {
    "APPLICATION": {"ACTIVE", "INACTIVE"},
    "ACTIVE": {"SUSPENDED", "INACTIVE"},
    "SUSPENDED": {"ACTIVE", "INACTIVE"},
    "INACTIVE": {"APPLICATION"},
}


def list_network_payers(db: Session, status_filter: str | None = None) -> list[Payer]:
    stmt = select(Payer).order_by(Payer.code)
    if status_filter:
        stmt = stmt.where(Payer.status == status_filter)
    return list(db.scalars(stmt.limit(200)))


def create_network_payer(db: Session, payload: PayerCreate, *, actor_user_id: UUID) -> Payer:
    code = payload.code.strip().upper()
    if db.scalar(select(Payer.id).where(Payer.code == code)) is not None:
        raise ValueError("PAYER_CODE_EXISTS")
    payer = Payer(name=payload.name.strip(), payer_type=payload.payer_type.strip(), code=code, status="APPLICATION")
    db.add(payer)
    db.flush()
    record_audit(db, action="CREATE_PAYER", resource_type="PAYER", resource_id=str(payer.id), result="SUCCESS", user_id=actor_user_id, metadata={"code": payer.code, "payer_type": payer.payer_type, "status": payer.status}, commit=False)
    db.commit()
    db.refresh(payer)
    return payer


def update_network_payer(db: Session, payer_id: UUID, payload: PayerUpdate, *, actor_user_id: UUID) -> Payer:
    payer = db.get(Payer, payer_id)
    if payer is None:
        raise ValueError("PAYER_NOT_FOUND")
    changes = {key: value.strip() for key, value in payload.model_dump(exclude_unset=True).items() if value is not None}
    if not changes:
        raise ValueError("NO_CHANGES")
    for key, value in changes.items():
        setattr(payer, key, value)
    db.flush()
    record_audit(db, action="UPDATE_PAYER", resource_type="PAYER", resource_id=str(payer.id), result="SUCCESS", user_id=actor_user_id, metadata={"changed_fields": sorted(changes)}, commit=False)
    db.commit()
    db.refresh(payer)
    return payer


def update_network_payer_status(db: Session, payer_id: UUID, new_status: str, reason: str, *, actor_user_id: UUID) -> Payer:
    payer = db.get(Payer, payer_id)
    if payer is None:
        raise ValueError("PAYER_NOT_FOUND")
    if payer.status == new_status:
        raise ValueError("PAYER_STATUS_UNCHANGED")
    if new_status not in PAYER_TRANSITIONS.get(payer.status, set()):
        raise ValueError("INVALID_PAYER_STATUS_TRANSITION")
    previous = payer.status
    payer.status = new_status
    db.flush()
    record_audit(db, action="UPDATE_PAYER_STATUS", resource_type="PAYER", resource_id=str(payer.id), result="SUCCESS", user_id=actor_user_id, metadata={"previous_status": previous, "new_status": new_status, "reason": reason.strip()}, commit=False)
    db.commit()
    db.refresh(payer)
    return payer


def list_network_payer_plans(db: Session, payer_id: UUID, status_filter: str | None = None) -> list[PayerPlan]:
    if db.get(Payer, payer_id) is None:
        raise ValueError("PAYER_NOT_FOUND")
    stmt = select(PayerPlan).where(PayerPlan.payer_id == payer_id).order_by(PayerPlan.code)
    if status_filter:
        stmt = stmt.where(PayerPlan.status == status_filter)
    return list(db.scalars(stmt.limit(200)))


def create_network_payer_plan(db: Session, payer_id: UUID, payload: PayerPlanCreate, *, actor_user_id: UUID) -> PayerPlan:
    payer = db.get(Payer, payer_id)
    if payer is None:
        raise ValueError("PAYER_NOT_FOUND")
    if payer.status != "ACTIVE":
        raise ValueError("PAYER_NOT_ACTIVE")
    code = payload.code.strip().upper()
    if db.scalar(select(PayerPlan.id).where(PayerPlan.payer_id == payer_id, PayerPlan.code == code)) is not None:
        raise ValueError("PAYER_PLAN_CODE_EXISTS")
    plan = PayerPlan(payer_id=payer_id, name=payload.name.strip(), code=code, status="ACTIVE")
    db.add(plan)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("PAYER_PLAN_CREATE_FAILED") from exc
    record_audit(db, action="CREATE_PAYER_PLAN", resource_type="PAYER_PLAN", resource_id=str(plan.id), result="SUCCESS", user_id=actor_user_id, metadata={"payer_id": str(payer_id), "code": plan.code}, commit=False)
    db.commit()
    db.refresh(plan)
    return plan


def update_network_payer_plan(db: Session, plan_id: UUID, payload: PayerPlanUpdate, *, actor_user_id: UUID) -> PayerPlan:
    plan = db.get(PayerPlan, plan_id)
    if plan is None:
        raise ValueError("PAYER_PLAN_NOT_FOUND")
    changes = {key: value.strip() for key, value in payload.model_dump(exclude_unset=True).items() if value is not None}
    if not changes:
        raise ValueError("NO_CHANGES")
    for key, value in changes.items():
        setattr(plan, key, value)
    db.flush()
    record_audit(db, action="UPDATE_PAYER_PLAN", resource_type="PAYER_PLAN", resource_id=str(plan.id), result="SUCCESS", user_id=actor_user_id, metadata={"changed_fields": sorted(changes)}, commit=False)
    db.commit()
    db.refresh(plan)
    return plan


def update_network_payer_plan_status(db: Session, plan_id: UUID, new_status: str, *, actor_user_id: UUID) -> PayerPlan:
    plan = db.get(PayerPlan, plan_id)
    if plan is None:
        raise ValueError("PAYER_PLAN_NOT_FOUND")
    if new_status not in {"ACTIVE", "INACTIVE"}:
        raise ValueError("INVALID_PAYER_PLAN_STATUS")
    if plan.status == new_status:
        raise ValueError("PAYER_PLAN_STATUS_UNCHANGED")
    previous = plan.status
    plan.status = new_status
    db.flush()
    record_audit(db, action="UPDATE_PAYER_PLAN_STATUS", resource_type="PAYER_PLAN", resource_id=str(plan.id), result="SUCCESS", user_id=actor_user_id, metadata={"previous_status": previous, "new_status": new_status}, commit=False)
    db.commit()
    db.refresh(plan)
    return plan
