"""Facility-scoped FHIR Patient $match operation for AfyaSync MPI.

Matching is deterministic and fail-safe: exact verified identifiers outrank
demographic matches, ambiguous results are returned as possible matches, and
no patient is auto-selected when multiple candidates remain.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.hie.service import _patient_resource
from app.patients.models import Person, AfyaIdentity


class MpiMatchError(ValueError):
    pass


def _hash_id(value: str) -> str:
    return sha256(value.strip().encode("utf-8")).hexdigest()


def _identifier_values(patient: dict) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in patient.get("identifier") or []:
        if not isinstance(item, dict):
            continue
        system = str(item.get("system") or "").lower()
        value = str(item.get("value") or "").strip()
        if not value:
            continue
        if "afya-id" in system:
            values["afya_id"] = value
        elif "national" in system or "national-id" in system:
            values["national_id"] = value
        elif "phone" in system:
            values["phone"] = value
    return values


def _demographics(patient: dict) -> tuple[str, str, date | None]:
    names = patient.get("name") or []
    official = next(
        (n for n in names if isinstance(n, dict) and n.get("use") == "official"),
        names[0] if names else {},
    )
    given = official.get("given") or []
    first = str(given[0]).strip() if given else ""
    last = str(official.get("family") or "").strip()
    dob = None
    if patient.get("birthDate"):
        try:
            dob = date.fromisoformat(str(patient["birthDate"])[:10])
        except ValueError:
            pass
    return first, last, dob


def build_patient_match_bundle(
    db: Session,
    *,
    patient: dict,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    if not isinstance(patient, dict) or patient.get("resourceType") != "Patient":
        raise MpiMatchError("PATIENT_RESOURCE_REQUIRED")

    identifiers = _identifier_values(patient)
    first, last, dob = _demographics(patient)
    candidates: dict[UUID, tuple[Person, AfyaIdentity | None, list[str], float]] = {}

    if identifiers.get("afya_id"):
        identity = db.scalar(
            select(AfyaIdentity).where(
                AfyaIdentity.afya_id == identifiers["afya_id"],
                AfyaIdentity.status == "ACTIVE",
            )
        )
        if identity:
            person = db.get(Person, identity.person_id)
            if person and person.status == "ACTIVE":
                candidates[person.id] = (person, identity, ["AFYA_ID"], 1.0)

    if identifiers.get("national_id"):
        person = db.scalar(
            select(Person).where(
                Person.national_id_hash == _hash_id(identifiers["national_id"]),
                Person.status == "ACTIVE",
            )
        )
        if person:
            identity = db.scalar(
                select(AfyaIdentity).where(
                    AfyaIdentity.person_id == person.id,
                    AfyaIdentity.status == "ACTIVE",
                )
            )
            if identity:
                candidates.setdefault(
                    person.id, (person, identity, ["NATIONAL_ID"], 1.0)
                )

    if first and last and dob:
        stmt = (
            select(Person, AfyaIdentity)
            .join(AfyaIdentity, AfyaIdentity.person_id == Person.id)
            .where(
                Person.status == "ACTIVE",
                Person.first_name.ilike(first),
                Person.last_name.ilike(last),
                Person.date_of_birth == dob,
                AfyaIdentity.status == "ACTIVE",
            )
        )
        if identifiers.get("phone"):
            stmt = stmt.where(Person.phone == identifiers["phone"])
        for person, identity in db.execute(stmt.limit(20)).all():
            reasons = ["FIRST_NAME", "LAST_NAME", "DATE_OF_BIRTH"]
            score = 0.85
            if identifiers.get("phone") and person.phone == identifiers["phone"]:
                reasons.append("PHONE")
                score = 0.95
            candidates.setdefault(person.id, (person, identity, reasons, score))

    resources = []
    for person, identity, reasons, score in candidates.values():
        resource = _patient_resource(db, person)
        resource["meta"] = {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"
            ]
        }
        resources.append({
            "fullUrl": f"urn:uuid:{resource['id']}",
            "resource": resource,
            "search": {"mode": "match", "score": score},
            "_afya_match_reasons": reasons,
            "_afya_identity": str(identity.afya_id) if identity else None,
        })

    resources.sort(key=lambda x: x["search"]["score"], reverse=True)
    if len(resources) == 1 and resources[0]["search"]["score"] == 1.0:
        outcome = "CERTAIN"
    elif resources:
        outcome = "POSSIBLE"
    else:
        outcome = "NO_MATCH"

    # Do not expose internal scoring reasons as FHIR fields.
    for entry in resources:
        entry.pop("_afya_match_reasons", None)
        entry.pop("_afya_identity", None)

    bundle = {
        "resourceType": "Bundle",
        "id": f"mpi-match-{uuid4()}",
        "type": "searchset",
        "total": len(resources),
        "entry": resources,
        "link": [{"relation": "self", "url": "Patient/$match"}],
    }

    # A searchset may legitimately contain zero Patients, so use the structural
    # validator without the one-Patient requirement.
    from app.hie.conformance import validate_bundle
    errors = validate_bundle(bundle, require_patient=False, require_provenance=False)
    if errors:
        raise MpiMatchError("HIE_FHIR_CONFORMANCE_FAILED:" + ",".join(errors))

    record_audit(
        db,
        action="HIE_MPI_PATIENT_MATCH",
        resource_type="Patient",
        resource_id=None,
        result=outcome,
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"candidate_count": len(resources), "match_outcome": outcome},
        commit=False,
    )
    return bundle
