from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.facilities.models import Department, Facility


def _next_facility_id(db: Session) -> str:
    count = db.scalar(select(func.count(Facility.id))) or 0
    return f"FAC-{count + 1:06d}"


def create_facility(db: Session, data: dict) -> Facility:
    facility = Facility(facility_id=_next_facility_id(db), **data)
    db.add(facility)
    db.commit()
    db.refresh(facility)
    return facility


def list_facilities(db: Session, limit: int = 50) -> list[Facility]:
    return list(db.scalars(select(Facility).order_by(Facility.name).limit(limit)))


def create_department(
    db: Session,
    facility_id: UUID,
    data: dict,
    *,
    actor_user_id: UUID | None = None,
) -> Department:
    facility = db.get(Facility, facility_id)
    if facility is None:
        raise ValueError("FACILITY_NOT_FOUND")

    department = Department(facility_id=facility_id, **data)
    db.add(department)
    db.flush()
    record_audit(
        db,
        action="CREATE_DEPARTMENT",
        resource_type="DEPARTMENT",
        resource_id=str(department.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"name": department.name, "code": department.code},
        commit=False,
    )
    db.commit()
    db.refresh(department)
    return department


def list_departments(db: Session, facility_id: UUID) -> list[Department]:
    return list(
        db.scalars(
            select(Department)
            .where(Department.facility_id == facility_id)
            .order_by(Department.name)
        )
    )
