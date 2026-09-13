from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.facilities.models import Facility
from app.rbac.models import Staff

_ALLOWED_STAFF_STATUSES = {"ACTIVE", "INACTIVE"}


def list_network_staff(
    db: Session,
    *,
    limit: int = 100,
    offset: int = 0,
    status: str | None = "ACTIVE",
    facility_id: UUID | None = None,
) -> tuple[list[dict], int]:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    filters = [Facility.status == "ACTIVE"]
    if status is not None:
        if status not in _ALLOWED_STAFF_STATUSES:
            raise ValueError("INVALID_STAFF_STATUS")
        filters.append(Staff.status == status)
    if facility_id is not None:
        filters.append(Staff.facility_id == facility_id)

    base = select(Staff.id).join(Facility, Facility.id == Staff.facility_id).where(*filters)
    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)

    rows = db.execute(
        select(
            Staff.id,
            Staff.facility_id,
            Facility.facility_id.label("facility_code"),
            Facility.name.label("facility_name"),
            Staff.person_id,
            Staff.employee_number,
            Staff.professional_number,
            Staff.department_id,
            Staff.status,
        )
        .join(Facility, Facility.id == Staff.facility_id)
        .where(*filters)
        .order_by(Facility.name, Staff.employee_number, Staff.id)
        .offset(offset)
        .limit(limit)
    ).mappings().all()
    return [dict(row) for row in rows], total
