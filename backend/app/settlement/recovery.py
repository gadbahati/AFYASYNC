from datetime import datetime,timezone
from decimal import Decimal
from uuid import UUID,uuid4
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.settlement.models import SettlementReconciliation
from app.claims.models import Claim
from sqlalchemy import ForeignKey,DateTime,Numeric,String,Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base

class RevenueRecoveryCase(Base):
    __tablename__="revenue_recovery_cases"
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    case_number:Mapped[str]=mapped_column(String(90),unique=True,index=True)
    facility_id:Mapped[UUID]=mapped_column(ForeignKey("facilities.id",ondelete="RESTRICT"),index=True)
    payer_id:Mapped[UUID|None]=mapped_column(ForeignKey("payers.id",ondelete="RESTRICT"),index=True)
    claim_id:Mapped[UUID|None]=mapped_column(ForeignKey("claims.id",ondelete="SET NULL"),index=True)
    batch_id:Mapped[UUID|None]=mapped_column(ForeignKey("settlement_batches.id",ondelete="SET NULL"),index=True)
    reconciliation_id:Mapped[UUID|None]=mapped_column(ForeignKey("settlement_reconciliations.id",ondelete="SET NULL"),index=True)
    reason:Mapped[str]=mapped_column(String(60),nullable=False)
    expected_amount:Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False,default=0)
    recovered_amount:Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False,default=0)
    outstanding_amount:Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False,default=0)
    status:Mapped[str]=mapped_column(String(30),nullable=False,default="OPEN",index=True)
    priority:Mapped[str]=mapped_column(String(20),nullable=False,default="NORMAL",index=True)
    owner_id:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"))
    external_reference:Mapped[str|None]=mapped_column(String(150))
    notes:Mapped[str|None]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())

class RecoveryUpdate(Base):
    __tablename__="recovery_case_updates"
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    recovery_case_id:Mapped[UUID]=mapped_column(ForeignKey("revenue_recovery_cases.id",ondelete="CASCADE"),index=True)
    status:Mapped[str]=mapped_column(String(30),nullable=False)
    amount:Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False,default=0)
    note:Mapped[str|None]=mapped_column(Text)
    actor_id:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())

def open_recovery(db:Session, reconciliation_id:UUID, facility_id:UUID, reason:str, priority:str, notes:str|None, actor_id:UUID):
    rec=db.get(SettlementReconciliation,reconciliation_id)
    if rec is None or rec.batch_id is None: raise ValueError("RECONCILIATION_NOT_FOUND")
    from app.settlement.models import SettlementBatch
    batch=db.get(SettlementBatch,rec.batch_id)
    if batch is None or batch.facility_id!=facility_id: raise ValueError("FACILITY_ACCESS_DENIED")
    if rec.difference>=0: raise ValueError("NO_UNDERPAYMENT_TO_RECOVER")
    from app.settlement.models import SettlementObligation
    # Recover the payer shortfall, not patient responsibility.
    expected=max(Decimal("0"),rec.expected_amount-rec.received_amount)
    existing=db.scalar(select(RevenueRecoveryCase).where(RevenueRecoveryCase.reconciliation_id==rec.id,RevenueRecoveryCase.status.in_(["OPEN","IN_PROGRESS","DISPUTED"])))
    if existing:return existing
    case=RevenueRecoveryCase(case_number=f"FXRC-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:9].upper()}",facility_id=facility_id,payer_id=batch.payer_id,batch_id=batch.id,reconciliation_id=rec.id,reason=reason,expected_amount=expected,recovered_amount=Decimal("0"),outstanding_amount=expected,status="OPEN",priority=priority,notes=notes)
    db.add(case);rec.recovery_status="OPEN";db.flush()
    db.add(RecoveryUpdate(recovery_case_id=case.id,status="OPEN",amount=Decimal("0"),note=notes,actor_id=actor_id))
    record_audit(db,actor_id,"OPEN_REVENUE_RECOVERY","revenue_recovery_case",str(case.id),{"amount":str(expected),"reason":reason})
    db.commit();db.refresh(case);return case

def update_recovery(db:Session,case_id:UUID,facility_id:UUID,status:str,recovered_amount:Decimal,note:str|None,actor_id:UUID):
    case=db.get(RevenueRecoveryCase,case_id)
    if case is None:raise ValueError("RECOVERY_CASE_NOT_FOUND")
    if case.facility_id!=facility_id:raise ValueError("FACILITY_ACCESS_DENIED")
    if status not in {"OPEN","IN_PROGRESS","DISPUTED","RECOVERED","WRITTEN_OFF","CLOSED"}:raise ValueError("INVALID_RECOVERY_STATUS")
    amount=Decimal(str(recovered_amount)).quantize(Decimal("0.01"))
    if amount<0 or amount>case.expected_amount:raise ValueError("INVALID_RECOVERY_AMOUNT")
    case.recovered_amount=amount
    case.outstanding_amount=max(Decimal("0"),case.expected_amount-amount)
    case.status=status
    if amount>=case.expected_amount:case.status="RECOVERED";case.outstanding_amount=Decimal("0")
    db.add(RecoveryUpdate(recovery_case_id=case.id,status=case.status,amount=amount,note=note,actor_id=actor_id))
    record_audit(db,actor_id,"UPDATE_REVENUE_RECOVERY","revenue_recovery_case",str(case.id),{"recovered":str(amount),"outstanding":str(case.outstanding_amount),"status":case.status})
    db.commit();db.refresh(case);return case

def recovery_overview(db:Session,facility_id:UUID):
    q=select(func.count(RevenueRecoveryCase.id),func.coalesce(func.sum(RevenueRecoveryCase.outstanding_amount),0),func.coalesce(func.sum(RevenueRecoveryCase.recovered_amount),0)).where(RevenueRecoveryCase.facility_id==facility_id,RevenueRecoveryCase.status.notin_(["RECOVERED","CLOSED","WRITTEN_OFF"]))
    count,outstanding,recovered=db.execute(q).one()
    return {"open_cases":count,"outstanding_amount":float(outstanding),"recovered_amount":float(recovered)}
