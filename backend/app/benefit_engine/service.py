from datetime import date
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.benefit_engine.models import BenefitRuleVersion

def find_rule(db: Session, *, payer_id: UUID, payer_plan_id: UUID|None, package_id: UUID|None, service_code: str|None, service_type: str|None, as_of: date):
    q=select(BenefitRuleVersion).where(BenefitRuleVersion.payer_id==payer_id,BenefitRuleVersion.status=="ACTIVE",BenefitRuleVersion.effective_from<=as_of,(BenefitRuleVersion.effective_to.is_(None))|(BenefitRuleVersion.effective_to>=as_of))
    if payer_plan_id:q=q.where((BenefitRuleVersion.payer_plan_id==payer_plan_id)|(BenefitRuleVersion.payer_plan_id.is_(None)))
    if package_id:q=q.where(BenefitRuleVersion.benefit_package_id==package_id)
    if service_code:q=q.where(BenefitRuleVersion.service_code==service_code)
    elif service_type:q=q.where(BenefitRuleVersion.service_type==service_type)
    return db.scalar(q.order_by(BenefitRuleVersion.version.desc()).limit(1))

def quote(db: Session, payload):
    as_of=payload.as_of or date.today(); gross=Decimal(str(payload.gross_amount)); rule=find_rule(db,payer_id=payload.payer_id,payer_plan_id=payload.payer_plan_id,package_id=payload.benefit_package_id,service_code=payload.service_code,service_type=payload.service_type,as_of=as_of)
    if rule is None:return {"matched":False,"rule_id":None,"package_id":None,"version":None,"tariff_amount":None,"gross_amount":float(gross),"allowed_amount":float(gross),"payer_amount":0.0,"patient_amount":float(gross),"currency":"KES","decision":"UNKNOWN","reason_code":"NO_ACTIVE_BENEFIT_RULE","requires_preauth":False}
    if rule.is_excluded:decision="INELIGIBLE";reason="SERVICE_EXCLUDED";payer=Decimal("0");allowed=Decimal("0")
    else:
        decision="CONDITIONAL" if rule.requires_preauth else "ELIGIBLE";reason="PREAUTH_REQUIRED" if rule.requires_preauth else "ACTIVE_BENEFIT_RULE";allowed=Decimal(str(rule.tariff_amount)) if rule.tariff_amount is not None else gross;allowed=min(gross,allowed);payer=(allowed*Decimal(str(rule.payer_percent))/Decimal("100"))-Decimal(str(rule.fixed_patient_copay));payer=max(Decimal("0"),payer);payer=min(payer,allowed);payer=min(payer,Decimal(str(rule.max_covered_amount))) if rule.max_covered_amount is not None else payer
    patient=max(Decimal("0"),gross-payer)
    return {"matched":True,"rule_id":rule.id,"package_id":rule.benefit_package_id,"version":rule.version,"tariff_amount":float(rule.tariff_amount) if rule.tariff_amount is not None else None,"gross_amount":float(gross),"allowed_amount":float(allowed),"payer_amount":float(payer),"patient_amount":float(patient),"currency":rule.currency,"decision":decision,"reason_code":reason,"requires_preauth":rule.requires_preauth}
