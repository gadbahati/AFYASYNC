from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.coverage.models import Coverage, Payer, PayerBenefitRule, PayerPlan
from app.coverage.schemas import BenefitRuleCreate, CoverageCreate


def create_coverage(db: Session, payload: CoverageCreate) -> Coverage:
    if payload.end_date and payload.start_date and payload.end_date < payload.start_date:
        raise ValueError("INVALID_COVERAGE_DATES")

    payer = db.get(Payer, payload.payer_id)
    if not payer or payer.status != "ACTIVE":
        raise ValueError("PAYER_NOT_FOUND")

    if payload.payer_plan_id:
        plan = db.get(PayerPlan, payload.payer_plan_id)
        if not plan or plan.payer_id != payload.payer_id or plan.status != "ACTIVE":
            raise ValueError("INVALID_PAYER_PLAN")

    coverage = Coverage(**payload.model_dump())
    db.add(coverage)
    db.commit()
    db.refresh(coverage)
    return coverage


def get_active_coverage(db: Session, person_id: UUID) -> list[Coverage]:
    today = date.today()
    statement = select(Coverage).where(
        Coverage.person_id == person_id,
        Coverage.status == "ACTIVE",
        (Coverage.start_date.is_(None) | (Coverage.start_date <= today)),
        (Coverage.end_date.is_(None) | (Coverage.end_date >= today)),
    ).order_by(Coverage.created_at.desc())
    return list(db.scalars(statement).all())


def create_benefit_rule(db: Session, payload: BenefitRuleCreate) -> PayerBenefitRule:
    if payload.effective_to and payload.effective_from and payload.effective_to < payload.effective_from:
        raise ValueError("INVALID_BENEFIT_DATES")
    payer = db.get(Payer, payload.payer_id)
    if not payer or payer.status != "ACTIVE":
        raise ValueError("PAYER_NOT_FOUND")
    if payload.payer_plan_id:
        plan = db.get(PayerPlan, payload.payer_plan_id)
        if not plan or plan.payer_id != payload.payer_id or plan.status != "ACTIVE":
            raise ValueError("INVALID_PAYER_PLAN")
    rule = PayerBenefitRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def get_verified_current_coverage(db: Session, person_id: UUID) -> Coverage | None:
    today = date.today()
    return db.scalar(
        select(Coverage)
        .where(
            Coverage.person_id == person_id,
            Coverage.status == "ACTIVE",
            Coverage.verification_status == "VERIFIED",
            (Coverage.start_date.is_(None) | (Coverage.start_date <= today)),
            (Coverage.end_date.is_(None) | (Coverage.end_date >= today)),
        )
        .order_by(Coverage.created_at.desc())
        .limit(1)
    )


def has_current_unverified_coverage(db: Session, person_id: UUID) -> bool:
    today = date.today()
    return db.scalar(
        select(Coverage.id)
        .where(
            Coverage.person_id == person_id,
            Coverage.status == "ACTIVE",
            Coverage.verification_status != "VERIFIED",
            (Coverage.start_date.is_(None) | (Coverage.start_date <= today)),
            (Coverage.end_date.is_(None) | (Coverage.end_date >= today)),
        )
        .limit(1)
    ) is not None


def find_benefit_rule(db: Session, coverage: Coverage, service_code: str, service_type: str) -> PayerBenefitRule | None:
    today = date.today()
    base = [
        PayerBenefitRule.payer_id == coverage.payer_id,
        PayerBenefitRule.status == "ACTIVE",
        (PayerBenefitRule.effective_from.is_(None) | (PayerBenefitRule.effective_from <= today)),
        (PayerBenefitRule.effective_to.is_(None) | (PayerBenefitRule.effective_to >= today)),
    ]
    candidates = list(db.scalars(select(PayerBenefitRule).where(*base)).all())

    def rank(rule: PayerBenefitRule) -> int:
        if rule.payer_plan_id == coverage.payer_plan_id and rule.service_code == service_code:
            return 4
        if rule.payer_plan_id == coverage.payer_plan_id and rule.service_type == service_type and rule.service_code is None:
            return 3
        if rule.payer_plan_id is None and rule.service_code == service_code:
            return 2
        if rule.payer_plan_id is None and rule.service_type == service_type and rule.service_code is None:
            return 1
        return 0

    ranked = sorted((rule for rule in candidates if rank(rule) > 0), key=rank, reverse=True)
    return ranked[0] if ranked else None


def calculate_charge_responsibility(db: Session, coverage: Coverage, *, amount: Decimal, service_code: str, service_type: str) -> tuple[Decimal, Decimal, UUID]:
    rule = find_benefit_rule(db, coverage, service_code, service_type)
    if rule is None:
        raise ValueError("COVERAGE_RULE_NOT_CONFIGURED")
    payer_percent = Decimal(str(rule.payer_percent)) / Decimal("100")
    payer_amount = amount * payer_percent
    if rule.max_covered_amount is not None:
        payer_amount = min(payer_amount, Decimal(str(rule.max_covered_amount)))
    patient_amount = amount - payer_amount
    copay = Decimal(str(rule.fixed_patient_copay))
    if copay > patient_amount:
        patient_amount = min(copay, amount)
        payer_amount = amount - patient_amount
    payer_amount = max(Decimal("0"), min(payer_amount, amount))
    patient_amount = amount - payer_amount
    return payer_amount.quantize(Decimal("0.01")), patient_amount.quantize(Decimal("0.01")), rule.id
