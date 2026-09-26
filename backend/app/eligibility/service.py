from datetime import date
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.coverage.models import Coverage, PayerBenefitRule
from app.eligibility.models import EligibilityDecision

def evaluate(db: Session, payload, actor_user_id=None):
    today=date.today()
    q=select(Coverage).where(Coverage.person_id==payload.person_id, Coverage.status=="ACTIVE", Coverage.verification_status=="VERIFIED")
    if payload.payer_id: q=q.where(Coverage.payer_id==payload.payer_id)
    if payload.payer_plan_id: q=q.where(Coverage.payer_plan_id==payload.payer_plan_id)
    coverages=list(db.scalars(q))
    active=[c for c in coverages if (c.start_date is None or c.start_date<=today) and (c.end_date is None or c.end_date>=today)]
    if not active:
        d="INELIGIBLE"; reason="NO_VERIFIED_ACTIVE_COVERAGE"; coverage=None; payer_amount=Decimal("0"); patient=Decimal(str(payload.gross_amount))
    else:
        coverage=active[0]; d="ELIGIBLE"; reason="VERIFIED_ACTIVE_COVERAGE"
        rq=select(PayerBenefitRule).where(PayerBenefitRule.payer_id==coverage.payer_id,PayerBenefitRule.status=="ACTIVE")
        if coverage.payer_plan_id: rq=rq.where((PayerBenefitRule.payer_plan_id==coverage.payer_plan_id)|(PayerBenefitRule.payer_plan_id.is_(None)))
        rules=list(db.scalars(rq))
        rule=next((r for r in rules if (payload.service_code and r.service_code==payload.service_code) or (payload.service_type and r.service_type==payload.service_type)),None)
        gross=Decimal(str(payload.gross_amount)); payer_amount=Decimal("0")
        if rule:
            if rule.is_excluded: d="INELIGIBLE"; reason="SERVICE_EXCLUDED"
            elif rule.requires_preauth: d="CONDITIONAL"; reason="PREAUTH_REQUIRED"
            else:
                payer_amount=(gross*Decimal(str(rule.payer_percent))/Decimal("100"))-Decimal(str(rule.fixed_patient_copay))
                payer_amount=max(Decimal("0"),payer_amount)
                if rule.max_covered_amount is not None: payer_amount=min(payer_amount,Decimal(str(rule.max_covered_amount)))
                patient=max(Decimal("0"),gross-payer_amount)
        else: patient=gross
    ev={"engine":"MULTI_PAYER_ELIGIBILITY_V1","as_of":today.isoformat(),"coverage_checked":len(coverages)}
    row=EligibilityDecision(person_id=payload.person_id,payer_id=coverage.payer_id if coverage else payload.payer_id,payer_plan_id=coverage.payer_plan_id if coverage else payload.payer_plan_id,service_code=payload.service_code,service_type=payload.service_type,decision=d,reason_code=reason,coverage_id=coverage.id if coverage else None,estimated_payer_amount=float(payer_amount),estimated_patient_amount=float(patient),evidence=ev)
    db.add(row); db.commit(); db.refresh(row)
    return row,ev
