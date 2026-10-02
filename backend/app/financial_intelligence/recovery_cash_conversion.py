from datetime import datetime,timedelta,timezone
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.settlement.recovery import RevenueRecoveryCase,RecoveryUpdate

def recovery_cash_conversion(db:Session,facility_id,days:int=90):
    since=datetime.now(timezone.utc)-timedelta(days=days)
    cases=list(db.scalars(select(RevenueRecoveryCase).where(RevenueRecoveryCase.facility_id==facility_id,RevenueRecoveryCase.created_at>=since)).all())
    rows=[]
    for c in cases:
        expected=float(c.expected_amount or 0); recovered=float(c.recovered_amount or 0); outstanding=float(c.outstanding_amount or 0)
        age=max(0,(datetime.now(timezone.utc)-c.created_at).days) if c.created_at else 0
        updates=int(db.scalar(select(func.count(RecoveryUpdate.id)).where(RecoveryUpdate.recovery_case_id==c.id)) or 0)
        conversion=round(recovered/expected*100,2) if expected else 0
        rows.append({"case_id":str(c.id),"case_number":c.case_number,"payer_id":str(c.payer_id) if c.payer_id else None,"expected":expected,"recovered":recovered,"outstanding":outstanding,"conversion_rate":conversion,"age_days":age,"updates":updates,"status":c.status,"priority":c.priority,"reason":c.reason})
    total_expected=sum(x["expected"] for x in rows);total_recovered=sum(x["recovered"] for x in rows);total_outstanding=sum(x["outstanding"] for x in rows)
    aging={"0_7":0,"8_30":0,"31_60":0,"61_90":0,"91_plus":0}
    for x in rows:
        k="0_7" if x["age_days"]<=7 else "8_30" if x["age_days"]<=30 else "31_60" if x["age_days"]<=60 else "61_90" if x["age_days"]<=90 else "91_plus"
        aging[k]+=x["outstanding"]
    actions=[]
    for x in rows:
        if x["outstanding"]>0 and x["age_days"]>30: actions.append({"case_id":x["case_id"],"action":"ESCALATE_RECOVERY","priority":"HIGH" if x["age_days"]>60 else "MEDIUM","reason":f"Recovery is {x['age_days']} days old with {x['outstanding']:,.0f} outstanding."})
        if x["expected"]>0 and x["conversion_rate"]<50 and x["age_days"]>14: actions.append({"case_id":x["case_id"],"action":"RECOVERY_STRATEGY_REVIEW","priority":"MEDIUM","reason":f"Cash conversion is {x['conversion_rate']}% after {x['age_days']} days."})
        if x["updates"]==0: actions.append({"case_id":x["case_id"],"action":"ADD_RECOVERY_ACTIVITY","priority":"LOW","reason":"No recovery activity update is recorded."})
    return {"window_days":days,"cases":rows,"totals":{"cases":len(rows),"expected":total_expected,"recovered":total_recovered,"outstanding":total_outstanding,"conversion_rate":round(total_recovered/total_expected*100,2) if total_expected else 0},"aging_outstanding":aging,"actions":actions}
