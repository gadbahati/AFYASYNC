from datetime import datetime
from uuid import UUID,uuid4
from sqlalchemy import DateTime,ForeignKey,Index,String,Text,func
from sqlalchemy.dialects.postgresql import JSONB,UUID as PGUUID
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base
class CareCoordinationCase(Base):
 __tablename__="care_coordination_cases"
 __table_args__=(Index("ix_care_coordination_status_due","status","due_at"),Index("ix_care_coordination_referral","referral_id"),Index("ix_care_coordination_patient","patient_id"))
 id: Mapped[UUID]=mapped_column(PGUUID(as_uuid=True),primary_key=True,default=uuid4)
 case_number: Mapped[str]=mapped_column(String(80),unique=True,nullable=False,index=True)
 referral_id: Mapped[UUID]=mapped_column(ForeignKey("referrals.id",ondelete="RESTRICT"),nullable=False,index=True)
 patient_id: Mapped[UUID]=mapped_column(ForeignKey("persons.id",ondelete="RESTRICT"),nullable=False,index=True)
 source_facility_id: Mapped[UUID]=mapped_column(ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False,index=True)
 destination_facility_id: Mapped[UUID]=mapped_column(ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False,index=True)
 status: Mapped[str]=mapped_column(String(30),nullable=False,default="OPEN",index=True)
 due_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),index=True)
 accepted_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
 appointment_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
 handoff_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
 closed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
 outcome: Mapped[str|None]=mapped_column(Text)
 notes: Mapped[str|None]=mapped_column(Text)
 evidence: Mapped[dict|None]=mapped_column(JSONB)
 created_by: Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"))
 created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
 updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),onupdate=func.now())
