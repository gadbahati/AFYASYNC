import hashlib
import hmac
import re
from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.config import settings
from app.patients.models import AfyaIdentity, PatientFacility, Person


def _hash_id(value: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), value.strip().encode(), hashlib.sha256).hexdigest()


def find_mpi_candidates(
    db: Session,
    *,
    facility_id: UUID,
    facility_ids: list[UUID] | None = None,
    first_name: str | None,
    last_name: str | None,
    date_of_birth: date | None,
    phone: str | None,
    national_id_number: str | None,
    limit: int = 20,
) -> list[dict]:
    conditions = []
    normalized_first = (first_name or "").strip()
    normalized_last = (last_name or "").strip()
    normalized_phone = (phone or "").strip()

    if national_id_number:
        if not re.fullmatch(r"\d{7,9}", national_id_number.strip()):
            raise ValueError("INVALID_ID_NUMBER")
        conditions.append(Person.national_id_hash == _hash_id(national_id_number))

    if normalized_first:
        conditions.append(Person.first_name.ilike(normalized_first))
    if normalized_last:
        conditions.append(Person.last_name.ilike(normalized_last))
    if date_of_birth:
        conditions.append(Person.date_of_birth == date_of_birth)
    if normalized_phone:
        conditions.append(Person.phone == normalized_phone)

    if not conditions:
        raise ValueError("MPI_SEARCH_REQUIRES_IDENTIFIER")

    scope_ids = facility_ids if facility_ids else [facility_id]
    stmt = (
        select(Person, AfyaIdentity)
        .join(AfyaIdentity, AfyaIdentity.person_id == Person.id)
        .join(PatientFacility, PatientFacility.patient_id == Person.id)
        .where(
            PatientFacility.facility_id.in_(scope_ids),
            PatientFacility.status == "ACTIVE",
            Person.status == "ACTIVE",
            or_(*conditions),
        )
        .limit(limit * 3)
    )

    rows = db.execute(stmt).all()
    results = []

    for person, identity in rows:
        reasons = []
        if national_id_number and person.national_id_hash == _hash_id(national_id_number):
            reasons.append("NATIONAL_ID")

        first_matches = bool(
            normalized_first
            and person.first_name.casefold() == normalized_first.casefold()
        )
        last_matches = bool(
            normalized_last
            and person.last_name.casefold() == normalized_last.casefold()
        )
        dob_matches = bool(date_of_birth and person.date_of_birth == date_of_birth)
        phone_matches = bool(normalized_phone and person.phone == normalized_phone)

        if first_matches:
            reasons.append("FIRST_NAME")
        if last_matches:
            reasons.append("LAST_NAME")
        if dob_matches:
            reasons.append("DATE_OF_BIRTH")
        if phone_matches:
            reasons.append("PHONE")

        if "NATIONAL_ID" in reasons:
            score = 100
        elif phone_matches and first_matches and last_matches:
            score = 90
        elif dob_matches and first_matches and last_matches:
            score = 80
        elif first_matches and last_matches:
            score = 55
        elif phone_matches and last_matches:
            score = 50
        elif phone_matches and first_matches:
            score = 50
        elif dob_matches and (first_matches or last_matches):
            score = 45
        else:
            score = 0

        # A single demographic field is too weak to interrupt registration.
        if score < 45:
            continue

        results.append({
            "patient_id": person.id,
            "afya_id": identity.afya_id,
            "full_name": " ".join(filter(None, [person.first_name, person.middle_name, person.last_name])),
            "date_of_birth": person.date_of_birth,
            "phone": person.phone,
            "match_score": score,
            "match_reasons": reasons,
        })

    results.sort(key=lambda item: (-item["match_score"], item["full_name"], str(item["patient_id"])))
    results = results[:limit]

    record_audit(
        db,
        action="MPI_CANDIDATE_SEARCH",
        resource_type="PERSON",
        resource_id=str(facility_id),
        result="SUCCESS",
        facility_id=facility_id,
        metadata={
            "candidate_count": len(results),
            "facility_scope_count": len(scope_ids),
            "searched_national_id": bool(national_id_number),
            "searched_phone": bool(normalized_phone),
            "searched_dob": bool(date_of_birth),
        },
        commit=True,
    )
    return results
