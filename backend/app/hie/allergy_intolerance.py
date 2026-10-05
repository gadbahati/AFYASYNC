"""FHIR AllergyIntolerance projection for AfyaSync's existing allergy records."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import Allergy
from app.facilities.models import Facility
from app.hie.conformance import assert_valid_bundle
from app.hie.service import _facility_organization_resource, _patient_resource, _require_enrollment
from app.hie.terminology_service import canonical_coding
from app.patients.models import Person


class AllergyIntoleranceFhirError(ValueError):
    pass


def build_allergy_intolerance_bundle(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    facility = db.get(Facility, facility_id)
    person = db.get(Person, patient_id)
    if facility is None:
        raise AllergyIntoleranceFhirError("FACILITY_NOT_FOUND")
    if person is None:
        raise AllergyIntoleranceFhirError("PATIENT_NOT_FOUND")
    try:
        person = _require_enrollment(db, patient_id, facility_id)
    except ValueError as exc:
        raise AllergyIntoleranceFhirError(str(exc)) from exc

    allergies = list(
        db.scalars(
            select(Allergy)
            .where(Allergy.patient_id == patient_id, Allergy.status == "ACTIVE")
            .order_by(Allergy.recorded_at)
        )
    )

    patient = _patient_resource(db, person)
    organization = _facility_organization_resource(db, facility_id)
    entries = [
        {"fullUrl": f"urn:uuid:{patient['id']}", "resource": patient},
        {"fullUrl": f"urn:uuid:{organization['id']}", "resource": organization},
    ]

    for allergy in allergies:
        coding = canonical_coding(
            db,
            source_system="AFYASYNC:ALLERGY",
            source_code=allergy.allergen,
            display=allergy.allergen,
        )
        if coding is None:
            raise AllergyIntoleranceFhirError(
                f"ALLERGY_CODE_NOT_MAPPED:{allergy.allergen}"
            )

        reaction = {}
        if allergy.reaction:
            reaction["manifestation"] = [{"text": allergy.reaction}]
        severity = {"MILD": "mild", "MODERATE": "moderate", "SEVERE": "severe"}.get((allergy.severity or "").upper())
        if severity:
            reaction["severity"] = severity

        resource = {
            "resourceType": "AllergyIntolerance",
            "id": str(uuid4()),
            "clinicalStatus": {"coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                "code": "active",
            }]},
            "verificationStatus": {"coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                "code": "confirmed",
            }]},
            "code": {"coding": [coding], "text": allergy.allergen},
            "patient": {"reference": f"Patient/{person.id}"},
            "recordedDate": allergy.created_at.isoformat() if allergy.created_at else datetime.now(timezone.utc).isoformat(),
        }
        if reaction:
            resource["reaction"] = [reaction]
        entries.append({
            "fullUrl": f"urn:uuid:{resource['id']}",
            "resource": resource,
        })

    bundle = {
        "resourceType": "Bundle",
        "id": str(uuid4()),
        "type": "collection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(entries),
        "entry": entries,
    }
    assert_valid_bundle(bundle)

    record_audit(
        db,
        action="HIE_ALLERGY_INTOLERANCE_EXPORT",
        resource_type="PATIENT",
        resource_id=str(patient_id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={"resource_count": len(entries)},
        commit=False,
    )
    return bundle
