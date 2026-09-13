"""Idempotent bootstrap for local/demo environments.

Creates a recognized pilot facility, System Administrator account, and the
canonical multi-coverage payers so the staff console can run standalone,
accept SHA members, or bill cash patients.

Credentials (change immediately outside controlled demos):
  username: afyasync.admin
  password: Kenya@Health2026
"""

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.coverage.models import Payer, PayerPlan
from app.facilities.models import Department, Facility
from app.patients.models import Person
from app.rbac.models import Permission, Role, RolePermission, Staff, StaffRole, User

DEMO_USERNAME = "afyasync.admin"
DEMO_PASSWORD = "Kenya@Health2026"
DEMO_FACILITY_CODE = "AFYA-PILOT-001"

CANONICAL_PAYERS = [
    {
        "code": "AFYASYNC",
        "name": "AfyaSync Membership",
        "payer_type": "AFYASYNC",
        "plan_code": "AFYASYNC-STANDARD",
        "plan_name": "AfyaSync Standard",
    },
    {
        "code": "SHA",
        "name": "Social Health Authority",
        "payer_type": "SHA",
        "plan_code": "SHA-SHIF",
        "plan_name": "SHA / SHIF",
    },
    {
        "code": "CASH",
        "name": "Self Pay (Cash)",
        "payer_type": "CASH",
        "plan_code": "CASH-DEFAULT",
        "plan_name": "Cash / Uninsured",
    },
]


def ensure_canonical_payers(db: Session) -> None:
    """Seed AFYASYNC, SHA, and CASH payers + default plans (idempotent)."""
    for item in CANONICAL_PAYERS:
        payer = db.scalar(select(Payer).where(Payer.code == item["code"]))
        if payer is None:
            payer = Payer(
                id=uuid4(),
                name=item["name"],
                payer_type=item["payer_type"],
                code=item["code"],
                status="ACTIVE",
                integration_status="NOT_CONFIGURED" if item["code"] == "SHA" else "INTERNAL",
            )
            db.add(payer)
            db.flush()
        else:
            payer.name = item["name"]
            payer.payer_type = item["payer_type"]
            payer.status = "ACTIVE"

        plan = db.scalar(
            select(PayerPlan).where(
                PayerPlan.payer_id == payer.id,
                PayerPlan.code == item["plan_code"],
            )
        )
        if plan is None:
            db.add(
                PayerPlan(
                    id=uuid4(),
                    payer_id=payer.id,
                    name=item["plan_name"],
                    code=item["plan_code"],
                    status="ACTIVE",
                )
            )
        else:
            plan.name = item["plan_name"]
            plan.status = "ACTIVE"


def ensure_demo_admin(db: Session) -> None:
    """Ensure pilot facility, roles, admin user, payers, and full permission grants exist."""
    ensure_canonical_payers(db)

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
