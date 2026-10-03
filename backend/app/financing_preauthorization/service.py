"""Financing preauthorization — request / decide / lookup.

Phase 106: drive CONDITIONAL decisions from the Universal Benefits &
Tariff Engine (primary), with eligibility engine as secondary signal.

Developer: BAHATI GAD WANGWE
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.financing_preauthorization.models import FinancingPreauthorization


class FinancingPreauthError(ValueError):
    pass


def _benefit_quote(db: Session, payload) -> dict:
    from app.benefit_engine.service import quote

    class _P:
        pass

    p = _P()
    p.payer_id = payload.payer_id
    p.payer_plan_id = getattr(payload, "payer_plan_id", None)
    p.benefit_package_id = None
    p.service_code = payload.service_code
    p.service_type = payload.service_type
    p.gross_amount = float(payload.requested_amount)
    p.as_of = None
    return quote(db, p)


def request(db: Session, *, facility_id, actor_user_id, payload):
    evidence: dict = {"source": "benefit_engine", "developer": "BAHATI GAD WANGWE"}
    coverage_id = payload.coverage_id
    needs_preauth = False
    decision_reason = "PREAUTH_REQUIRED"

    # Primary: Universal Benefits & Tariff Engine
    try:
        bq = _benefit_quote(db, payload)
        evidence["benefit_quote"] = {
            "decision": bq.get("decision"),
            "reason_code": bq.get("reason_code"),
            "requires_preauth": bq.get("requires_preauth"),
            "rule_id": str(bq["rule_id"]) if bq.get("rule_id") else None,
            "payer_amount": bq.get("payer_amount"),
            "patient_amount": bq.get("patient_amount"),
        }
        if bq.get("decision") == "INELIGIBLE":
            raise FinancingPreauthError(bq.get("reason_code") or "SERVICE_EXCLUDED")
        if bq.get("decision") == "UNKNOWN":
            raise FinancingPreauthError("NO_ACTIVE_BENEFIT_RULE")
        if bq.get("requires_preauth") or bq.get("decision") == "CONDITIONAL":
            needs_preauth = True
            decision_reason = bq.get("reason_code") or "PREAUTH_REQUIRED"
        else:
            # Engine says fully eligible — still allow explicit preauth only if eligibility says CONDITIONAL
            needs_preauth = False
    except FinancingPreauthError:
        raise
    except Exception as exc:
        evidence["benefit_quote_error"] = type(exc).__name__

    # Secondary: eligibility engine (coverage-aware)
    try:
        from app.eligibility.schemas import EligibilityRequest
        from app.eligibility.service import evaluate

        eligibility, elig_evidence = evaluate(
            db,
            EligibilityRequest(
                person_id=payload.person_id,
                service_code=payload.service_code,
                service_type=payload.service_type,
                payer_id=payload.payer_id,
                payer_plan_id=None,
                gross_amount=payload.requested_amount,
            ),
            actor_user_id=actor_user_id,
        )
        evidence["eligibility"] = elig_evidence or {"decision": eligibility.decision}
        if eligibility.coverage_id:
            coverage_id = eligibility.coverage_id
        if eligibility.decision == "INELIGIBLE":
            raise FinancingPreauthError(eligibility.reason_code or "INELIGIBLE")
        if eligibility.decision == "CONDITIONAL":
            needs_preauth = True
            decision_reason = eligibility.reason_code or decision_reason
        elif eligibility.decision == "ELIGIBLE" and not needs_preauth:
            raise FinancingPreauthError("PREAUTH_NOT_REQUIRED")
        elif eligibility.decision == "UNKNOWN" and not needs_preauth:
            raise FinancingPreauthError("ELIGIBILITY_UNKNOWN")
    except FinancingPreauthError:
        raise
    except Exception as exc:
        evidence["eligibility_error"] = type(exc).__name__
        if not needs_preauth:
            raise FinancingPreauthError("PREAUTH_NOT_REQUIRED") from exc

    if not needs_preauth:
        raise FinancingPreauthError("PREAUTH_NOT_REQUIRED")

    row = FinancingPreauthorization(
        authorization_number=f"FXPA-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:10].upper()}",
        person_id=payload.person_id,
        facility_id=facility_id,
        coverage_id=coverage_id,
        payer_id=payload.payer_id,
        service_code=payload.service_code,
        service_type=payload.service_type,
        requested_amount=Decimal(str(payload.requested_amount)),
        status="PENDING",
        decision_reason=decision_reason,
        evidence=evidence,
    )
    db.add(row)
    record_audit(
        db,
        action="FINANCING_PREAUTH_REQUESTED",
        resource_type="FINANCING_PREAUTHORIZATION",
        resource_id=str(row.id),
        result="PENDING",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=payload.person_id,
        metadata={
            "authorization_number": row.authorization_number,
            "payer_id": str(payload.payer_id),
            "decision_reason": decision_reason,
        },
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return row


def decide(db: Session, *, authorization_id, facility_id, actor_user_id, payload):
    row = db.scalar(
        select(FinancingPreauthorization)
        .where(
            FinancingPreauthorization.id == authorization_id,
            FinancingPreauthorization.facility_id == facility_id,
        )
        .with_for_update()
    )
    if row is None:
        raise FinancingPreauthError("PREAUTH_NOT_FOUND")
    if row.status not in {"PENDING", "SUBMITTED"}:
        raise FinancingPreauthError("PREAUTH_NOT_DECIDABLE")
    approved = Decimal(str(payload.approved_amount)).quantize(Decimal("0.01"))
    requested = Decimal(str(row.requested_amount)).quantize(Decimal("0.01"))
    if approved > requested:
        raise FinancingPreauthError("APPROVED_AMOUNT_EXCEEDS_REQUEST")
    if payload.status == "REJECTED" and approved != 0:
        raise FinancingPreauthError("REJECTED_AMOUNT_MUST_BE_ZERO")
    if payload.status in {"AUTHORIZED", "CONDITIONAL"} and approved == 0:
        raise FinancingPreauthError("INVALID_APPROVED_AMOUNT")
    row.status = payload.status
    row.approved_amount = approved
    row.external_reference = payload.external_reference.strip() if payload.external_reference else None
    row.decided_at = datetime.now(timezone.utc)
    record_audit(
        db,
        action="FINANCING_PREAUTH_DECIDED",
        resource_type="FINANCING_PREAUTHORIZATION",
        resource_id=str(row.id),
        result=payload.status,
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=row.person_id,
        metadata={
            "approved_amount": str(approved),
            "external_reference": row.external_reference,
        },
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return row


def list_for_facility(
    db: Session,
    *,
    facility_id: UUID,
    status: str | None = None,
    person_id: UUID | None = None,
    limit: int = 50,
) -> list[FinancingPreauthorization]:
    q = select(FinancingPreauthorization).where(FinancingPreauthorization.facility_id == facility_id)
    if status:
        q = q.where(FinancingPreauthorization.status == status)
    if person_id:
        q = q.where(FinancingPreauthorization.person_id == person_id)
    q = q.order_by(FinancingPreauthorization.requested_at.desc()).limit(min(limit, 200))
    return list(db.scalars(q).all())


def find_active_authorization(
    db: Session,
    *,
    facility_id: UUID,
    person_id: UUID,
    payer_id: UUID,
    service_code: str | None,
) -> FinancingPreauthorization | None:
    """Return latest AUTHORIZED (or CONDITIONAL with amount) preauth for claim gating."""
    q = select(FinancingPreauthorization).where(
        FinancingPreauthorization.facility_id == facility_id,
        FinancingPreauthorization.person_id == person_id,
        FinancingPreauthorization.payer_id == payer_id,
        FinancingPreauthorization.status.in_(["AUTHORIZED", "CONDITIONAL"]),
    )
    if service_code:
        q = q.where(
            (FinancingPreauthorization.service_code == service_code)
            | (FinancingPreauthorization.service_code.is_(None))
        )
    return db.scalar(q.order_by(FinancingPreauthorization.decided_at.desc().nullslast()).limit(1))
