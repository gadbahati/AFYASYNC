"""Idempotent bootstrap for local/demo environments.

Creates a recognized pilot facility and System Administrator account so the
staff console can be monitored end-to-end without manual SQL.

Credentials (change immediately outside controlled demos):
  username: afyasync.admin
  password: Kenya@Health2026
"""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.facilities.models import Department, Facility
from app.patients.models import Person
from app.rbac.models import Permission, Role, RolePermission, Staff, StaffRole, User

DEMO_USERNAME = "afyasync.admin"
DEMO_PASSWORD = "Kenya@Health2026"
DEMO_FACILITY_CODE = "AFYA-PILOT-001"


def ensure_demo_admin(db: Session) -> None:
    """Ensure pilot facility, roles, admin user, and full permission grants exist."""
    # Roles catalog
    role_names = [
        "System Administrator",
        "Hospital Administrator",
        "Reception",
        "Doctor",
        "Nurse",
        "Lab Technician",
        "Pharmacist",
        "Cashier",
        "Finance",
    ]
    roles: dict[str, Role] = {}
    for name in role_names:
        role = db.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(id=uuid4(), name=name, description=f"{name} role")
            db.add(role)
            db.flush()
        roles[name] = role

    # Grant System Administrator every permission currently in the catalog
    admin_role = roles["System Administrator"]
    permission_ids = list(db.scalars(select(Permission.id)))
    for permission_id in permission_ids:
        exists = db.scalar(
            select(RolePermission.role_id).where(
                RolePermission.role_id == admin_role.id,
                RolePermission.permission_id == permission_id,
            )
        )
        if exists is None:
            db.add(RolePermission(role_id=admin_role.id, permission_id=permission_id))

    facility = db.scalar(select(Facility).where(Facility.facility_id == DEMO_FACILITY_CODE))
    if facility is None:
        facility = Facility(
            id=uuid4(),
            facility_id=DEMO_FACILITY_CODE,
            name="AfyaSync National Pilot Facility",
            facility_type="HOSPITAL",
            county="Nairobi",
            sub_county="Westlands",
            address="Nairobi, Kenya",
            phone="+254700000000",
            email="pilot@afyasync.ke",
            status="ACTIVE",
        )
        db.add(facility)
        db.flush()

    department = db.scalar(
        select(Department).where(
            Department.facility_id == facility.id,
            Department.code == "OPD",
        )
    )
    if department is None:
        department = Department(
            id=uuid4(),
            facility_id=facility.id,
            name="Outpatient",
            code="OPD",
            status="ACTIVE",
        )
        db.add(department)
        db.flush()

    user = db.scalar(select(User).where(User.username == DEMO_USERNAME))
    if user is None:
        person = Person(
            id=uuid4(),
            first_name="AfyaSync",
            last_name="Administrator",
            sex="OTHER",
            phone="+254700000001",
            email="admin@afyasync.ke",
            status="ACTIVE",
        )
        db.add(person)
        db.flush()
        user = User(
            id=uuid4(),
            person_id=person.id,
            username=DEMO_USERNAME,
            phone="+254700000001",
            password_hash=hash_password(DEMO_PASSWORD),
            mfa_enabled=False,
            status="ACTIVE",
        )
        db.add(user)
        db.flush()
    else:
        # Keep password aligned for demo monitoring account
        user.password_hash = hash_password(DEMO_PASSWORD)
        user.status = "ACTIVE"
        if user.person_id is None:
            person = Person(
                id=uuid4(),
                first_name="AfyaSync",
                last_name="Administrator",
                status="ACTIVE",
            )
            db.add(person)
            db.flush()
            user.person_id = person.id

    assert user.person_id is not None
    staff = db.scalar(
        select(Staff).where(
            Staff.person_id == user.person_id,
            Staff.facility_id == facility.id,
        )
    )
    if staff is None:
        staff = Staff(
            id=uuid4(),
            facility_id=facility.id,
            person_id=user.person_id,
            employee_number="EMP-ADMIN-001",
            department_id=department.id,
            status="ACTIVE",
        )
        db.add(staff)
        db.flush()
    else:
        staff.status = "ACTIVE"
        staff.department_id = department.id

    link = db.scalar(
        select(StaffRole.staff_id).where(
            StaffRole.staff_id == staff.id,
            StaffRole.role_id == admin_role.id,
            StaffRole.facility_id == facility.id,
        )
    )
    if link is None:
        db.add(
            StaffRole(
                staff_id=staff.id,
                role_id=admin_role.id,
                facility_id=facility.id,
            )
        )

    db.commit()
