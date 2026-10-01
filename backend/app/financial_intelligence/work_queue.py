from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class CollectionWorkItem(Base):
    __tablename__="collection_work_items"
    id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
    facility_id:Mapped[UUID]=mapped_column(ForeignKey("facilities.id",ondelete="RESTRICT"),index=True)
    source_type:Mapped[str]=mapped_column(String(40),nullable=False)
    source_id:Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),nullable=False)
    title:Mapped[str]=mapped_column(String(220),nullable=False)
    priority:Mapped[str]=mapped_column(String(20),nullable=False,default="NORMAL",index=True)
    status:Mapped[str]=mapped_column(String(30),nullable=False,default="OPEN",index=True)
    assigned_to:Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"),nullable=True)
    due_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    outstanding_amount:Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=False,default=0)
    note:Mapped[str|None]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now(),nullable=False)
