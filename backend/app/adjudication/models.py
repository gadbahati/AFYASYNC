from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class ClaimAdjudication(Base):
    __tablename__="claim_adjudications"
    id: Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    claim_id: Mapped[UUID]=mapped_column(ForeignKey("claims.id",ondelete="RESTRICT"),nullable=False,index=True,unique=True)
    decision: Mapped[str]=mapped_column(String(40),nullable=False,index=True)
    submitted_amount: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False)
    allowed_amount: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False)
    patient_amount: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False)
    reason_code: Mapped[str]=mapped_column(String(100),nullable=False)
    evidence: Mapped[dict|None]=mapped_column(JSONB)
    adjudicated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    adjudicated_by: Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"))

class ClaimLineAdjudication(Base):
    __tablename__="claim_line_adjudications"
    id: Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    adjudication_id: Mapped[UUID]=mapped_column(ForeignKey("claim_adjudications.id",ondelete="CASCADE"),nullable=False,index=True)
    claim_item_id: Mapped[UUID]=mapped_column(ForeignKey("claim_items.id",ondelete="RESTRICT"),nullable=False,index=True)
    submitted_amount: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False)
    allowed_amount: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False)
    decision: Mapped[str]=mapped_column(String(40),nullable=False)
    reason_code: Mapped[str]=mapped_column(String(100),nullable=False)
    evidence: Mapped[dict|None]=mapped_column(JSONB)
