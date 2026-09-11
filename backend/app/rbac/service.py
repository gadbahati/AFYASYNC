from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.facilities.models import Department, Facility
from app.patients.models import AfyaIdentity, Person
from app.rbac.models import Permission, Role, Staff, StaffRole

_ALLOWED_STAFF_STATUSES = {"ACTIVE", "INACTIVE"}


def create_role(db: Session, data: dict) -> Role:
    role = Role(**data)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def create_permission(db: Session, data: dict) -> Permission:
    permission = Permission(**data)
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


def create_staff(
    db: Session,
    data: dict,
    *,
    actor_user_id: UUID | None = None,
) -> Staff:
    facility_id = data["facility_id"]
    if facility_id is None:
        raise ValueError("FACILITY_CONTEXT_REQUIRED")
    if db.get(Facility, facility_id) is None:
        raise ValueError("FACILITY_NOT_FOUND")
    if db.get(Person, data["person_id"]) is None:
        raise ValueError("PERSON_NOT_FOUND")

    department_id = data.get("department_id")
    if department_id is not None:
        department = db.get(Department, department_id)
        if department is None or department.facility_id != facility_id:
            raise ValueError("INVALID_DEPARTMENT")

    existing = db.scalar(
        select(Staff).where(
            Staff.facility_id == facility_id,
            Staff.person_id == data["person_id"],
        )
    )
    if existing is not None:
        if existing.status == "ACTIVE":
            raise ValueError("STAFF_ALREADY_EXISTS")
        # Reactivate inactive membership at this facility
        existing.status = "ACTIVE"
        if data.get("employee_number"):
            existing.employee_number = data["employee_number"]
        if "professional_number" in data:
            existing.professional_number = data.get("professional_number")
        if "department_id" in data:
            existing.department_id = department_id
        db.flush()
        record_audit(
            db,
            action="REACTIVATE_STAFF",
            resource_type="STAFF",
            resource_id=str(existing.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=facility_id,
            metadata={"person_id": str(data["person_id"])},
            commit=False,
        )
        db.commit()
        db.refresh(existing)
        return existing

    # Prevent duplicate employee number within the same facility
    dup_emp = db.scalar(
        select(Staff.id).where(
            Staff.facility_id == facility_id,
            Staff.employee_number == data["employee_number"],
        )
    )
    if dup_emp is not None:
        raise ValueError("DUPLICATE_EMPLOYEE_NUMBER")

    staff = Staff(
        facility_id=facility_id,
        person_id=data["person_id"],
        employee_number=data["employee_number"],
        professional_number=data.get("professional_number"),
        department_id=department_id,
        status="ACTIVE",
    )
    db.add(staff)
    db.flush()
    record_audit(
        db,
        action="CREATE_STAFF",
        resource_type="STAFF",
        resource_id=str(staff.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"person_id": str(data["person_id"]), "employee_number": staff.employee_number},
        commit=False,
    )
    db.commit()
    db.refresh(staff)
    return staff


def list_staff(
    db: Session,
    facility_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
    status: str | None = "ACTIVE",
) -> tuple[list[Staff], int]:
    if facility_id is None:
        raise ValueError("FACILITY_CONTEXT_REQUIRED")
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)

    filters = [Staff.facility_id == facility_id]
    if status is not None:
        if status not in _ALLOWED_STAFF_STATUSES:
            raise ValueError("INVALID_STAFF_STATUS")
        filters.append(Staff.status == status)

    total = int(db.scalar(select(func.count()).select_from(Staff).where(*filters)) or 0)
    items = list(
        db.scalars(
            select(Staff)
            .where(*filters)
            .order_by(Staff.employee_number, Staff.id)
            .offset(offset)
            .limit(limit)
        )
    )
    return items, total


def update_staff_status(
    db: Session,
    staff_id: UUID,
    facility_id: UUID,
    status: str,
    *,
    actor_user_id: UUID | None = None,
) -> Staff:
    if facility_id is None:
        raise ValueError("FACILITY_CONTEXT_REQUIRED")
    if status not in _ALLOWED_STAFF_STATUSES:
        raise ValueError("INVALID_STAFF_STATUS")

    staff = db.get(Staff, staff_id)
    if staff is None or staff.facility_id != facility_id:
        raise ValueError("STAFF_NOT_FOUND")
    if staff.status == status:
        raise ValueError("STAFF_STATUS_UNCHANGED")

    previous = staff.status
    staff.status = status
    db.flush()
    record_audit(
        db,
        action="UPDATE_STAFF_STATUS",
        resource_type="STAFF",
        resource_id=str(staff.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"previous_status": previous, "new_status": status},
        commit=False,
    )
    db.commit()
    db.refresh(staff)
    return staff


def assign_staff_role(
    db: Session,
    staff_id: UUID,
    role_id: UUID,
    facility_id: UUID,
    *,
    actor_user_id: UUID | None = None,
) -> StaffRole:
    if facility_id is None:
        raise ValueError("FACILITY_CONTEXT_REQUIRED")

    staff = db.get(Staff, staff_id)
    if staff is None or staff.facility_id != facility_id:
        raise ValueError("STAFF_NOT_FOUND")
    if staff.status != "ACTIVE":
        raise ValueError("STAFF_NOT_ACTIVE")

    role = db.get(Role, role_id)
    if role is None:
        raise ValueError("ROLE_NOT_FOUND")

    existing = db.get(StaffRole, {"staff_id": staff_id, "role_id": role_id, "facility_id": facility_id})
    if existing is not None:
        raise ValueError("ROLE_ALREADY_ASSIGNED")

    link = StaffRole(staff_id=staff_id, role_id=role_id, facility_id=facility_id)
    db.add(link)
    db.flush()
    record_audit(
        db,
        action="ASSIGN_STAFF_ROLE",
        resource_type="STAFF_ROLE",
        resource_id=f"{staff_id}:{role_id}",
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"staff_id": str(staff_id), "role_id": str(role_id), "role_name": role.name},
        commit=False,
    )
    db.commit()
    db.refresh(link)
    return link


def remove_staff_role(
    db: Session,
    staff_id: UUID,
    role_id: UUID,
    facility_id: UUID,
    *,
    actor_user_id: UUID | None = None,
) -> None:
    if facility_id is None:
        raise ValueError("FACILITY_CONTEXT_REQUIRED")

    staff = db.get(Staff, staff_id)
    if staff is None or staff.facility_id != facility_id:
        raise ValueError("STAFF_NOT_FOUND")

    link = db.get(StaffRole, {"staff_id": staff_id, "role_id": role_id, "facility_id": facility_id})
    if link is None:
        raise ValueError("ROLE_NOT_ASSIGNED")

    db.delete(link)
    db.flush()
    record_audit(
        db,
        action="REMOVE_STAFF_ROLE",
        resource_type="STAFF_ROLE",
        resource_id=f"{staff_id}:{role_id}",
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"staff_id": str(staff_id), "role_id": str(role_id)},
        commit=False,
    )
    db.commit()


def list_staff_roles(db: Session, staff_id: UUID, facility_id: UUID) -> list[StaffRole]:
    staff = db.get(Staff, staff_id)
    if staff is None or staff.facility_id != facility_id:
        raise ValueError("STAFF_NOT_FOUND")
    return list(
        db.scalars(
            select(StaffRole).where(
                StaffRole.staff_id == staff_id,
                StaffRole.facility_id == facility_id,
            )
        )
    )


def get_identity_for_person(db: Session, person_id: UUID) -> AfyaIdentity | None:
    return db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person_id))
