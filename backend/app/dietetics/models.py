from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, String, Text, Numeric, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class NutritionAssessment(Base):
    __tablename__ = "nutrition_assessments"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    weight: Mapped[str | None] = mapped_column(String(30))
    height: Mapped[str | None] = mapped_column(String(30))
    bmi: Mapped[float | None] = mapped_column(Numeric(8,2))
    nutrition_risk: Mapped[str] = mapped_column(String(40), default="LOW")
    dietary_requirements: Mapped[str | None] = mapped_column(Text)
    allergies: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    assessed_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class DietOrder(Base):
    __tablename__ = "diet_orders"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="RESTRICT"), index=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("persons.id", ondelete="RESTRICT"), index=True)
    encounter_id: Mapped[UUID | None] = mapped_column(ForeignKey("encounters.id", ondelete="RESTRICT"), index=True)
    diet_type: Mapped[str] = mapped_column(String(80), nullable=False)
    texture: Mapped[str | None] = mapped_column(String(60))
    calories: Mapped[str | None] = mapped_column(String(40))
    restrictions: Mapped[str | None] = mapped_column(Text)
    instructions: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    ordered_by: Mapped[UUID] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"))
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
