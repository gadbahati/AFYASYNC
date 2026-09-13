from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.coverage.models import Payer, PayerBenefitRule, PayerPlan
from app.coverage.benefit_admin_schemas import BenefitRuleAdminCreate, BenefitRuleAdminUpdate



def _validate_scope(payer_id: UUID, payer_plan_id: UUID | None, db: Session) -> None:
    payer = db.get(Payer, payer_id)
    if payer is None:
        raise ValueError("PAYER_NOT_FOUND")
    if payer.status != "ACTIVE":
        raise ValueError("PAYER_NOT_ACTIVE")
    if payer_plan_id is not None:
        plan = db.get(PayerPlan, payer_plan_id)
        if plan is None or plan.payer_id != payer_id:
            raise ValueError("INVALID_PAYER_PLAN")
        if plan.status != "ACTIVE":
            raise ValueError("PAYER_PLAN_NOT_ACTIVE")


def list_network_benefit_rules(
    db: Session,
    payer_id: UUID | None = None,
    payer_plan_id: UUID | None = None,
    status_filter: str | None = None,
) -> list[PayerBenefitRule]:
    stmt = select(PayerBenefitRule).order_by(PayerBenefitRule.created_at.desc())
    if payer_id is not None:
        stmt = stmt.where(PayerBenefitRule.payer_id == payer_id)
    if payer_plan_id is not None:
        stmt = stmt.where(PayerBenefitRule.payer_plan_id == payer_plan_id)
    if status_filter:
        stmt = stmt.where(PayerBenefitRule.status == status_filter)
    return list(db.scalars(stmt.limit(500)))


def create_network_benefit_rule(
    db: Session,
    payload: BenefitRuleAdminCreate,
    *,
    actor_user_id: UUID,
) -> PayerBenefitRule:
    _validate_scope(payload.payer_id, payload.payer_plan_id, db)
    rule = PayerBenefitRule(
        payer_id=payload.payer_id,
        payer_plan_id=payload.payer_plan_id,
        service_code=payload.service_code.strip().upper() if payload.service_code else None,
        service_type=payload.service_type.strip().upper() if payload.service_type else None,
        payer_percent=payload.payer_percent,
        fixed_patient_copay=payload.fixed_patient_copay,
        max_covered_amount=payload.max_covered_amount,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        status="ACTIVE",
    )
    db.add(rule)
    db.flush()
    record_audit(
        db,
        action="CREATE_BENEFIT_RULE",
        resource_type="PAYER_BENEFIT_RULE",
        resource_id=str(rule.id),
        result="SUCCESS",
        user_id=actor_user_id,
        metadata={
            "payer_id": str(rule.payer_id),
            "payer_plan_id": str(rule.payer_plan_id) if rule.payer_plan_id else None,
            "service_code": rule.service_code,
            "service_type": rule.service_type,
            "payer_percent": str(rule.payer_percent),
            "fixed_patient_copay": str(rule.fixed_patient_copay),
            "max_covered_amount": str(rule.max_covered_amount) if rule.max_covered_amount is not None else None,
            "effective_from": rule.effective_from.isoformat() if rule.effective_from else None,
            "effective_to": rule.effective_to.isoformat() if rule.effective_to else None,
        },
        commit=False,
    )
    db.commit()
    db.refresh(rule)
    return rule


def update_network_benefit_rule(
    db: Session,
    rule_id: UUID,
    payload: BenefitRuleAdminUpdate,
    *,
    actor_user_id: UUID,
) -> PayerBenefitRule:
    rule = db.get(PayerBenefitRule, rule_id)
    if rule is None:
        raise ValueError("BENEFIT_RULE_NOT_FOUND")
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise ValueError("NO_CHANGES")
    effective_from = changes.get("effective_from", rule.effective_from)
    effective_to = changes.get("effective_to", rule.effective_to)
    if effective_from and effective_to and effective_to < effective_from:
        raise ValueError("INVALID_BENEFIT_DATES")
    if "service_code" in changes:
        changes["service_code"] = changes["service_code"].strip().upper() if changes["service_code"] else None
    if "service_type" in changes:
        changes["service_type"] = changes["service_type"].strip().upper() if changes["service_type"] else None
    if "service_code" in changes and "service_type" in changes and not changes["service_code"] and not changes["service_type"]:
        raise ValueError("BENEFIT_SCOPE_REQUIRED")
    if "service_code" in changes and not changes["service_code"] and not rule.service_type:
        raise ValueError("BENEFIT_SCOPE_REQUIRED")
    if "service_type" in changes and not changes["service_type"] and not rule.service_code:
        raise ValueError("BENEFIT_SCOPE_REQUIRED")
    for key, value in changes.items():
        setattr(rule, key, value)
    db.flush()
    record_audit(
        db,
        action="UPDATE_BENEFIT_RULE",
        resource_type="PAYER_BENEFIT_RULE",
        resource_id=str(rule.id),
        result="SUCCESS",
        user_id=actor_user_id,
        metadata={"changed_fields": sorted(changes)},
        commit=False,
    )
    db.commit()
    db.refresh(rule)
    return rule


def update_network_benefit_rule_status(
    db: Session,
    rule_id: UUID,
    new_status: str,
    reason: str,
    *,
    actor_user_id: UUID,
) -> PayerBenefitRule:
    rule = db.get(PayerBenefitRule, rule_id)
    if rule is None:
        raise ValueError("BENEFIT_RULE_NOT_FOUND")
    if new_status not in {"ACTIVE", "INACTIVE"}:
        raise ValueError("INVALID_BENEFIT_RULE_STATUS")
    if rule.status == new_status:
        raise ValueError("BENEFIT_RULE_STATUS_UNCHANGED")
    previous = rule.status
    rule.status = new_status
    db.flush()
    record_audit(
        db,
        action="UPDATE_BENEFIT_RULE_STATUS",
        resource_type="PAYER_BENEFIT_RULE",
        resource_id=str(rule.id),
        result="SUCCESS",
        user_id=actor_user_id,
        metadata={"previous_status": previous, "new_status": new_status, "reason": reason.strip()},
        commit=False,
    )
    db.commit()
    db.refresh(rule)
    return rule
