from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.facilities.models import Department, Facility

_ALLOWED_FACILITY_STATUSES = {"APPLICATION", "ACTIVE", "SUSPENDED", "INACTIVE"}
_ALLOWED_DEPARTMENT_STATUSES = {"ACTIVE", "INACTIVE"}


def _next_facility_id(db: Session) -> str:
    count = db.scalar(select(func.count(Facility.id))) or 0
    return f"FAC-{count + 1:06d}"


def create_facility(
    db: Session,
    data: dict,
    *,
    actor_user_id: UUID | None = None,
) -> Facility:
    facility = Facility(facility_id=_next_facility_id(db), **data)
    db.add(facility)
    db.flush()
    record_audit(
        db,
        action="CREATE_FACILITY",
        resource_type="FACILITY",
        resource_id=str(facility.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility.id,
        metadata={"facility_id": facility.facility_id, "name": facility.name},
        commit=False,
    )
    db.commit()
    db.refresh(facility)
    return facility


def list_facilities(db: Session, limit: int = 50) -> list[Facility]:
    limit = min(max(limit, 1), 100)
    return list(db.scalars(select(Facility).order_by(Facility.name).limit(limit)))


def get_facility(db: Session, facility_id: UUID) -> Facility | None:
    return db.get(Facility, facility_id)


def update_facility(
    db: Session,
    facility_id: UUID,
    data: dict,
    *,
    actor_user_id: UUID | None = None,
) -> Facility:
    facility = db.get(Facility, facility_id)
    if facility is None:
        raise ValueError("FACILITY_NOT_FOUND")
    changes = {k: v for k, v in data.items() if v is not None}
    if not changes:
        raise ValueError("NO_CHANGES")
    for field, value in changes.items():
        setattr(facility, field, value)
    db.flush()
    record_audit(
        db,
        action="UPDATE_FACILITY",
        resource_type="FACILITY",
        resource_id=str(facility.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"changed_fields": sorted(changes.keys())},
        commit=False,
    )
    db.commit()
    db.refresh(facility)
    return facility


def update_facility_status(
    db: Session,
    facility_id: UUID,
    status: str,
    *,
    actor_user_id: UUID | None = None,
) -> Facility:
    if status not in _ALLOWED_FACILITY_STATUSES:
        raise ValueError("INVALID_FACILITY_STATUS")
    facility = db.get(Facility, facility_id)
    if facility is None:
        raise ValueError("FACILITY_NOT_FOUND")
    if facility.status == status:
        raise ValueError("FACILITY_STATUS_UNCHANGED")
    previous = facility.status
    facility.status = status
    db.flush()
    record_audit(
        db,
        action="UPDATE_FACILITY_STATUS",
        resource_type="FACILITY",
        resource_id=str(facility.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"previous_status": previous, "new_status": status},
        commit=False,
    )
    db.commit()
    db.refresh(facility)
    return facility


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

    existing = db.scalar(
        select(Department).where(
            Department.facility_id == facility_id,
            Department.code == data["code"],
        )
    )
    if existing is not None:
        raise ValueError("DEPARTMENT_CODE_EXISTS")

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


def update_department_status(
    db: Session,
    facility_id: UUID,
    department_id: UUID,
    status: str,
    *,
    actor_user_id: UUID | None = None,
) -> Department:
    if status not in _ALLOWED_DEPARTMENT_STATUSES:
        raise ValueError("INVALID_DEPARTMENT_STATUS")
    department = db.get(Department, department_id)
    if department is None or department.facility_id != facility_id:
        raise ValueError("DEPARTMENT_NOT_FOUND")
    if department.status == status:
        raise ValueError("DEPARTMENT_STATUS_UNCHANGED")
    previous = department.status
    department.status = status
    db.flush()
    record_audit(
        db,
        action="UPDATE_DEPARTMENT_STATUS",
        resource_type="DEPARTMENT",
        resource_id=str(department.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"previous_status": previous, "new_status": status},
        commit=False,
    )
    db.commit()
    db.refresh(department)
    return department
