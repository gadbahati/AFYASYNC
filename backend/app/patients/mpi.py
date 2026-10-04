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

    # Search is restricted to people already known to this facility/network.
    stmt = (
        select(Person, AfyaIdentity)
        .join(AfyaIdentity, AfyaIdentity.person_id == Person.id)
        .join(PatientFacility, PatientFacility.patient_id == Person.id)
        .where(
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
            Person.status == "ACTIVE",
            or_(*conditions),
        )
        .order_by(Person.last_name, Person.first_name, Person.id)
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    results = []
    for person, identity in rows:
        reasons = []
        if normalized_first and person.first_name.casefold() == normalized_first.casefold():
            reasons.append("FIRST_NAME")
        if normalized_last and person.last_name.casefold() == normalized_last.casefold():
            reasons.append("LAST_NAME")
        if date_of_birth and person.date_of_birth == date_of_birth:
            reasons.append("DATE_OF_BIRTH")
        if normalized_phone and person.phone == normalized_phone:
            reasons.append("PHONE")
        if national_id_number and person.national_id_hash == _hash_id(national_id_number):
            reasons.append("NATIONAL_ID")
        score = min(100, len(reasons) * 20 + (50 if "NATIONAL_ID" in reasons else 0))
        results.append({
            "patient_id": person.id,
            "afya_id": identity.afya_id,
            "full_name": " ".join(filter(None, [person.first_name, person.middle_name, person.last_name])),
            "date_of_birth": person.date_of_birth,
            "phone": person.phone,
            "match_score": score,
            "match_reasons": reasons,
        })
    record_audit(
        db,
        action="MPI_CANDIDATE_SEARCH",
        resource_type="PERSON",
        resource_id=str(facility_id),
        result="SUCCESS",
        facility_id=facility_id,
        metadata={"candidate_count": len(results), "searched_national_id": bool(national_id_number), "searched_phone": bool(normalized_phone), "searched_dob": bool(date_of_birth)},
        commit=True,
    )
    return results
