from datetime import datetime
from uuid import UUID,uuid4
from sqlalchemy import DateTime,ForeignKey,Index,String,func
from sqlalchemy.dialects.postgresql import UUID as PGUUID,JSONB
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base

class ContractActivationEvent(Base):
    __tablename__="contract_activation_events"
    __table_args__=(Index("ix_contract_activation_events_contract_created","contract_id","created_at"),)
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    facility_id:Mapped[UUID]=mapped_column(ForeignKey("facilities.id",ondelete="CASCADE"),nullable=False,index=True)
    contract_id:Mapped[UUID]=mapped_column(ForeignKey("provider_network_contracts.id",ondelete="CASCADE"),nullable=False,index=True)
    event_type:Mapped[str]=mapped_column(String(60),nullable=False)
    status:Mapped[str]=mapped_column(String(30),nullable=False)
    actor_id:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="RESTRICT"))
    details:Mapped[dict|None]=mapped_column(JSONB)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
