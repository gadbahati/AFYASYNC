from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Facility(Base):
    __tablename__ = "facilities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    facility_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    facility_type: Mapped[str] = mapped_column(String(50))
    registration_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    county: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sub_county: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="APPLICATION", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    departments: Mapped[list["Department"]] = relationship(back_populates="facility")
    registry_record: Mapped["FacilityRegistryRecord | None"] = relationship(back_populates="facility", uselist=False, cascade="all, delete-orphan")
    registry_history: Mapped[list["FacilityRegistryHistory"]] = relationship(back_populates="facility", cascade="all, delete-orphan")


class FacilityRegistryRecord(Base):
    __tablename__ = "facility_registry_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50), default="KMHFR")
    source_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    mfl_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    keph_level: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    ownership: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    ward: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    constituency: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    services: Mapped[list | dict | None] = mapped_column(JSON, nullable=True)
    raw_record: Mapped[dict] = mapped_column(JSON, default=dict)
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    facility: Mapped[Facility] = relationship(back_populates="registry_record")


class FacilityRegistryHistory(Base):
    __tablename__ = "facility_registry_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(50), default="KMHFR")
    action: Mapped[str] = mapped_column(String(30))
    changed_fields: Mapped[list] = mapped_column(JSON, default=list)
    before_record: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_record: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    facility: Mapped[Facility] = relationship(back_populates="registry_history")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    facility_id: Mapped[UUID] = mapped_column(ForeignKey("facilities.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    code: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    facility: Mapped[Facility] = relationship(back_populates="departments")
