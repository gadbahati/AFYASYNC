"""Kenya Core provider and care-team identity builders.

This module maps AfyaSync's existing Staff/Person/Facility/Department records
to national FHIR provider resources without inventing registry namespaces.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.facilities.models import Department, Facility
from app.patients.models import Person
from app.rbac.models import Role, Staff, StaffRole, User


KENYA_CORE_BASE = "https://fhir.dha.go.ke/core/StructureDefinition/"
PRACTITIONER_PROFILE = KENYA_CORE_BASE + "practitioner-sha-ke|1.0.0"
PRACTITIONER_ROLE_PROFILE = KENYA_CORE_BASE + "kenya-core-practitionerrole|1.0.0"
LOCATION_PROFILE = KENYA_CORE_BASE + "kenya-core-location|1.0.0"


def staff_for_user(db: Session, *, user_id: UUID, facility_id: UUID) -> Staff | None:
    user = db.get(User, user_id)
    if user is None or user.person_id is None:
        return None
    return db.scalar(
        select(Staff).where(
            Staff.person_id == user.person_id,
            Staff.facility_id == facility_id,
            Staff.status == "ACTIVE",
        )
    )


def _person(db: Session, staff: Staff) -> Person:
    person = db.get(Person, staff.person_id)
    if person is None:
        raise ValueError("STAFF_PERSON_NOT_FOUND")
    return person


def practitioner_resource(db: Session, staff: Staff) -> dict:
    person = _person(db, staff)
    resource = {
        "resourceType": "Practitioner",
        "id": str(staff.id),
        "meta": {"profile": [PRACTITIONER_PROFILE]},
        "active": staff.status == "ACTIVE",
        "name": [{
            "use": "official",
            "family": person.last_name,
            "given": [x for x in [person.first_name, person.middle_name] if x],
        }],
    }
    if person.phone:
        resource["telecom"] = [{"system": "phone", "value": person.phone, "use": "work"}]
    if person.email:
        resource.setdefault("telecom", []).append({"system": "email", "value": person.email, "use": "work"})
    if person.date_of_birth:
        resource["birthDate"] = person.date_of_birth.isoformat()
    if staff.professional_number:
        # No national namespace is asserted here until the responsible council
        # registry is explicitly configured and verified.
        resource["identifier"] = [{
            "use": "official",
            "type": {"text": "Professional registration number"},
            "value": staff.professional_number,
        }]
    return resource


def location_resource(db: Session, *, facility: Facility, department: Department) -> dict:
    return {
        "resourceType": "Location",
        "id": str(department.id),
        "meta": {"profile": [LOCATION_PROFILE]},
        "status": "active" if department.status == "ACTIVE" else "inactive",
        "name": department.name,
        "description": f"{department.name} department at {facility.name}",
        "managingOrganization": {"reference": f"Organization/{facility.id}"},
        "identifier": [{"use": "usual", "value": department.code}],
    }


def practitioner_role_resource(
    db: Session,
    *,
    staff: Staff,
    facility: Facility,
    department: Department | None,
) -> dict:
    role_rows = db.execute(
        select(Role.name)
        .join(StaffRole, StaffRole.role_id == Role.id)
        .where(
            StaffRole.staff_id == staff.id,
            StaffRole.facility_id == facility.id,
        )
        .order_by(Role.name)
    ).scalars().all()

    role_code = role_rows[0] if role_rows else "Healthcare professional"
    resource = {
        "resourceType": "PractitionerRole",
        "id": str(staff.id),
        "meta": {"profile": [PRACTITIONER_ROLE_PROFILE]},
        "active": staff.status == "ACTIVE",
        "practitioner": {"reference": f"Practitioner/{staff.id}"},
        "organization": {"reference": f"Organization/{facility.id}"},
        "code": [{"text": role_code}],
    }
    if department is not None:
        resource["location"] = [{"reference": f"Location/{department.id}"}]
    return resource


def provider_identity_resources(
    db: Session,
    *,
    facility_id: UUID,
    staff_id: UUID,
) -> list[dict]:
    staff = db.get(Staff, staff_id)
    if staff is None or staff.facility_id != facility_id or staff.status != "ACTIVE":
        raise ValueError("STAFF_NOT_FOUND")
    facility = db.get(Facility, facility_id)
    if facility is None:
        raise ValueError("FACILITY_NOT_FOUND")
    department = db.get(Department, staff.department_id) if staff.department_id else None
    if department is not None and department.facility_id != facility_id:
        raise ValueError("DEPARTMENT_NOT_FOUND")

    resources = [practitioner_resource(db, staff)]
    if department is not None:
        resources.append(location_resource(db, facility=facility, department=department))
    resources.append(
        practitioner_role_resource(
            db,
            staff=staff,
            facility=facility,
            department=department,
        )
    )
    return resources


def actor_provider_identity_resources(
    db: Session,
    *,
    user_id: UUID | None,
    facility_id: UUID,
) -> list[dict]:
    if user_id is None:
        return []
    staff = staff_for_user(db, user_id=user_id, facility_id=facility_id)
    if staff is None:
        return []
    return provider_identity_resources(db, facility_id=facility_id, staff_id=staff.id)
