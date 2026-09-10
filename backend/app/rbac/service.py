from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.facilities.models import Department, Facility
from app.patients.models import AfyaIdentity, Person
from app.rbac.models import Permission, Role, Staff


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


def create_staff(db: Session, data: dict) -> Staff:
    if db.get(Facility, data["facility_id"]) is None:
        raise ValueError("FACILITY_NOT_FOUND")
    if db.get(Person, data["person_id"]) is None:
        raise ValueError("PERSON_NOT_FOUND")
    department_id = data.get("department_id")
    if department_id is not None:
        department = db.get(Department, department_id)
        if department is None or department.facility_id != data["facility_id"]:
            raise ValueError("INVALID_DEPARTMENT")

    staff = Staff(**data)
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


def list_staff(db: Session, facility_id: UUID, limit: int = 100) -> list[Staff]:
    return list(
        db.scalars(
            select(Staff)
            .where(Staff.facility_id == facility_id)
            .order_by(Staff.employee_number)
            .limit(limit)
        )
    )


def get_identity_for_person(db: Session, person_id: UUID) -> AfyaIdentity | None:
    return db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person_id))
