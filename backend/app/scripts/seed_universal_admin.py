"""One-shot development/pilot administrator bootstrap.

This script is intentionally never invoked automatically in production.
Provide credentials explicitly through the environment or function arguments;
there is no built-in password or demo credential.
"""

from __future__ import annotations

import os
import sys

from sqlalchemy import select, text

from app.auth.security import hash_password
from app.database import SessionLocal
from app.facilities.models import Facility
from app.patients.models import Person
from app.rbac.models import Staff, User

DEFAULT_USERNAME = "afyasync.admin"
DEFAULT_FACILITY_CODE = "AFYA-DEMO-001"
DEFAULT_FACILITY_NAME = "AfyaSync Pilot Facility"


def seed_universal_admin(*, username: str | None = None, password: str | None = None, reset_password: bool | None = None) -> dict:
    username = (username or os.getenv("UNIVERSAL_ADMIN_USERNAME") or DEFAULT_USERNAME).strip()
    password = password or os.getenv("UNIVERSAL_ADMIN_PASSWORD")
    if not password:
        raise ValueError("UNIVERSAL_ADMIN_PASSWORD is required; no default password exists")
    if len(password) < 16:
        raise ValueError("administrator password must be at least 16 characters")
    if reset_password is None:
        reset_password = os.getenv("SEED_RESET_PASSWORD", "").strip().lower() in {"1", "true", "yes"}
    if not username:
        raise ValueError("username is required")

    db = SessionLocal()
    try:
        db.execute(text("CREATE EXTENSION IF NOT EXISTS citext"))
        db.commit()
        facility = db.scalar(select(Facility).where(Facility.facility_id == DEFAULT_FACILITY_CODE))
        if facility is None:
            facility = Facility(facility_id=DEFAULT_FACILITY_CODE, name=DEFAULT_FACILITY_NAME, facility_type="HOSPITAL", county="Nairobi", status="ACTIVE")
            db.add(facility)
            db.flush()
        elif facility.status != "ACTIVE":
            facility.status = "ACTIVE"

        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            person = Person(first_name="AfyaSync", last_name="Administrator", status="ACTIVE")
            db.add(person)
            db.flush()
            user = User(person_id=person.id, username=username, password_hash=hash_password(password), status="ACTIVE")
            db.add(user)
            db.flush()
            created_user = True
        else:
            created_user = False
            if user.status != "ACTIVE":
                user.status = "ACTIVE"
            if reset_password:
                user.password_hash = hash_password(password)
            if user.person_id is None:
                person = Person(first_name="AfyaSync", last_name="Administrator", status="ACTIVE")
                db.add(person)
                db.flush()
                user.person_id = person.id

        assert user.person_id is not None
        staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == facility.id))
        if staff is None:
            db.add(Staff(facility_id=facility.id, person_id=user.person_id, employee_number="ADMIN-001", status="ACTIVE"))
        elif staff.status != "ACTIVE":
            staff.status = "ACTIVE"
        db.commit()
        return {"username": username, "facility_code": facility.facility_id, "facility_name": facility.name, "created_user": created_user, "password_reset": bool(reset_password or created_user)}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    flag = os.getenv("SEED_UNIVERSAL_ADMIN", "").strip().lower()
    if flag not in {"1", "true", "yes"} and "--force" not in sys.argv:
        print("SEED_UNIVERSAL_ADMIN is not enabled. Pass --force to run anyway.")
        return 2
    result = seed_universal_admin()
    print("Universal admin ready:", {k: v for k, v in result.items() if k != "password"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
