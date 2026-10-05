"""FHIR MedicationAdministration interoperability using persisted AfyaSync medication actions.

Only completed/recorded administration actions are exported; dispensing and stock
movements are not represented as administrations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.hie.terminology_service import canonical_coding
from app.patients.models import Person
from app.pharmacy.models import Medication, MedicationAction, PrescriptionItem
from app.rbac.models import Staff


class MedicationAdministrationFhirError(ValueError):
    pass


_ACTION_STATUS = {
    "ADMINISTERED": "completed",
    "GIVEN": "completed",
    "COMPLETED": "completed",
    "NOT_GIVEN": "not-done",
    "REFUSED": "not-done",
    "CANCELLED": "entered-in-error",
}


def build_medication_administration_bundle(
    db: Session,
    *,
    action_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    action = db.get(MedicationAction, action_id)
    if action is None:
        raise MedicationAdministrationFhirError("NOT_FOUND")

    encounter = db.get(Encounter, action.encounter_id)
    if encounter is None:
        raise MedicationAdministrationFhirError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise MedicationAdministrationFhirError("ACCESS_DENIED")

    person = db.get(Person, encounter.patient_id)
    if person is None:
        raise MedicationAdministrationFhirError("PATIENT_NOT_FOUND")

    if action.prescription_item_id:
        item = db.get(PrescriptionItem, action.prescription_item_id)
        if item is None or item.prescription_id is None:
            raise MedicationAdministrationFhirError("PRESCRIPTION_ITEM_NOT_FOUND")
    else:
        item = None

    medication = db.get(Medication, action.medication_id)
    if medication is None or medication.status != "ACTIVE":
        raise MedicationAdministrationFhirError("MEDICATION_NOT_FOUND")

    coding = canonical_coding(
        db,
        source_system="AFYASYNC:MEDICATION",
        source_code=medication.code,
        display=medication.name,
    )
    if coding is None:
        raise MedicationAdministrationFhirError(
            f"MEDICATION_CODE_NOT_MAPPED:{medication.code}"
        )

    performer = db.get(Staff, action.performed_by)
    if performer is None or performer.facility_id != facility_id or performer.status != "ACTIVE":
        raise MedicationAdministrationFhirError("PERFORMER_NOT_FOUND")

    facility = db.get(Facility, facility_id)
    if facility is None:
        raise MedicationAdministrationFhirError("FACILITY_NOT_FOUND")

    patient = _patient_resource(db, person)
    organization = _facility_organization_resource(db, facility_id)
    provider_resources = provider_identity_resources(
        db, facility_id=facility_id, staff_id=performer.id
    )
    role = next((r for r in provider_resources if r["resourceType"] == "PractitionerRole"), None)

    entries = [
        {"fullUrl": f"urn:uuid:{patient['id']}", "resource": patient},
        {"fullUrl": f"urn:uuid:{organization['id']}", "resource": organization},
    ]
    for resource in provider_resources:
        entries.append({
            "fullUrl": f"urn:uuid:{resource['resourceType']}/{resource['id']}",
            "resource": resource,
        })

    status = _ACTION_STATUS.get((action.action_type or "").upper())
    if status is None:
        raise MedicationAdministrationFhirError(
            f"UNSUPPORTED_ACTION_TYPE:{action.action_type}"
        )

    administration = {
        "resourceType": "MedicationAdministration",
        "id": str(uuid4()),
        "status": status,
        "medicationCodeableConcept": {"coding": [coding], "text": medication.name},
        "subject": {"reference": f"Patient/{person.id}"},
        "context": {"reference": f"Encounter/{encounter.id}"},
        "effectiveDateTime": (
            action.performed_at.isoformat()
            if action.performed_at else datetime.now(timezone.utc).isoformat()
        ),
        "performer": [{
            "actor": {
                "reference": (
                    f"PractitionerRole/{role['id']}"
                    if role else f"Practitioner/{performer.id}"
                )
            }
        }],
        "dosage": {
            "text": " ".join(
                p for p in [
                    item.dose if item else None,
                    item.frequency if item else None,
                    item.route if item else None,
                    action.notes,
                ] if p
            ) or None,
            **({"route": {"text": item.route}} if item and item.route else {}),
        },
        "quantity": {"value": float(action.quantity), "unit": medication.unit or "unit"},
        "note": [{"text": action.notes}] if action.notes else [],
    }

    entries.append({
        "fullUrl": f"urn:uuid:{administration['id']}",
        "resource": administration,
    })

    provenance = {
        "resourceType": "Provenance",
        "id": str(uuid4()),
        "target": [{"reference": f"MedicationAdministration/{administration['id']}"}],
        "recorded": datetime.now(timezone.utc).isoformat(),
        "agent": [{
            "type": {"text": "performer"},
            "who": {
                "reference": (
                    f"PractitionerRole/{role['id']}"
                    if role else f"Practitioner/{performer.id}"
                )
            },
            "onBehalfOf": {"reference": f"Organization/{facility_id}"},
        }],
        "activity": {"text": "HIE medication administration export"},
    }
    entries.append({"fullUrl": f"urn:uuid:{provenance['id']}", "resource": provenance})

    bundle = {
        "resourceType": "Bundle",
        "id": str(uuid4()),
        "type": "collection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(entries),
        "entry": entries,
        "meta": {"tag": [{"system": "https://afyasync.health.ke/hie", "code": "MEDICATION_ADMINISTRATION"}]},
    }
    assert_valid_bundle(bundle)

    record_audit(
        db,
        action="HIE_MEDICATION_ADMINISTRATION_EXPORT",
        resource_type="MEDICATION_ACTION",
        resource_id=str(action.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person.id,
        metadata={"resource_count": len(entries), "status": status},
        commit=False,
    )
    return bundle
