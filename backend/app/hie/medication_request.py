"""FHIR MedicationRequest interoperability for existing AfyaSync prescriptions.

This projection never invents a national medication code. A medication must have
an active AFYASYNC:MEDICATION terminology mapping before it is exported as a
FHIR MedicationRequest.
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
from app.pharmacy.models import Medication, Prescription, PrescriptionItem
from app.rbac.models import Staff


class MedicationRequestFhirError(ValueError):
    pass


def build_medication_request_bundle(
    db: Session,
    *,
    prescription_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise MedicationRequestFhirError("NOT_FOUND")

    encounter = db.get(Encounter, prescription.encounter_id)
    if encounter is None:
        raise MedicationRequestFhirError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise MedicationRequestFhirError("ACCESS_DENIED")

    person = db.get(Person, prescription.patient_id)
    if person is None:
        raise MedicationRequestFhirError("PATIENT_NOT_FOUND")

    facility = db.get(Facility, facility_id)
    if facility is None:
        raise MedicationRequestFhirError("FACILITY_NOT_FOUND")

    prescriber = db.get(Staff, prescription.prescribed_by)
    if prescriber is None or prescriber.facility_id != facility_id or prescriber.status != "ACTIVE":
        raise MedicationRequestFhirError("PRESCRIBER_NOT_FOUND")

    items = list(
        db.scalars(
            select(PrescriptionItem)
            .where(PrescriptionItem.prescription_id == prescription.id)
            .order_by(PrescriptionItem.id)
        )
    )
    if not items:
        raise MedicationRequestFhirError("PRESCRIPTION_ITEMS_REQUIRED")

    patient = _patient_resource(db, person)
    organization = _facility_organization_resource(db, facility_id)
    provider_resources = provider_identity_resources(
        db, facility_id=facility_id, staff_id=prescriber.id
    )

    entries = [
        {"fullUrl": f"urn:uuid:{patient['id']}", "resource": patient},
        {"fullUrl": f"urn:uuid:{organization['id']}", "resource": organization},
    ]
    for resource in provider_resources:
        entries.append({
            "fullUrl": f"urn:uuid:{resource['resourceType']}/{resource['id']}",
            "resource": resource,
        })

    practitioner_role = next(
        (r for r in provider_resources if r["resourceType"] == "PractitionerRole"),
        None,
    )

    for item in items:
        medication = db.get(Medication, item.medication_id)
        if medication is None or medication.status != "ACTIVE":
            raise MedicationRequestFhirError("MEDICATION_NOT_FOUND")

        coding = canonical_coding(
            db,
            source_system="AFYASYNC:MEDICATION",
            source_code=medication.code,
            display=medication.name,
        )
        if coding is None:
            raise MedicationRequestFhirError(
                f"MEDICATION_CODE_NOT_MAPPED:{medication.code}"
            )

        dosage_text = " ".join(
            part for part in [
                item.dose,
                item.frequency,
                item.duration,
                item.route,
                item.instructions,
            ] if part
        )

        medication_request = {
            "resourceType": "MedicationRequest",
            "id": str(uuid4()),
            "status": (prescription.status or "active").lower(),
            "intent": "order",
            "identifier": [{
                "system": "https://afyasync.health.ke/identifier/prescription",
                "value": prescription.prescription_id,
            }],
            "medicationCodeableConcept": {
                "coding": [coding],
                "text": medication.name,
            },
            "subject": {"reference": f"Patient/{person.id}"},
            "encounter": {"reference": f"Encounter/{encounter.id}"},
            "authoredOn": prescription.created_at.isoformat() if prescription.created_at else datetime.now(timezone.utc).isoformat(),
            "requester": {
                "reference": f"PractitionerRole/{practitioner_role['id']}"
            } if practitioner_role else {
                "reference": f"Practitioner/{prescriber.id}"
            },
            "dosageInstruction": [{
                "text": dosage_text,
                **({"route": {"text": item.route}} if item.route else {}),
            }],
            "dispenseRequest": {
                "quantity": {
                    "value": float(item.quantity),
                    "unit": medication.unit or "unit",
                }
            },
        }
        entries.append({
            "fullUrl": f"urn:uuid:{medication_request['id']}",
            "resource": medication_request,
        })

    provenance = {
        "resourceType": "Provenance",
        "id": str(uuid4()),
        "target": [
            {"reference": f"{e['resource']['resourceType']}/{e['resource']['id']}"}
            for e in entries
        ],
        "recorded": datetime.now(timezone.utc).isoformat(),
        "agent": [{
            "type": {"text": "author"},
            "who": {
                "reference": (
                    f"PractitionerRole/{practitioner_role['id']}"
                    if practitioner_role
                    else f"Practitioner/{prescriber.id}"
                )
            },
            "onBehalfOf": {"reference": f"Organization/{facility_id}"},
        }],
        "activity": {"text": "HIE medication request export"},
    }
    entries.append({
        "fullUrl": f"urn:uuid:{provenance['id']}",
        "resource": provenance,
    })

    bundle = {
        "resourceType": "Bundle",
        "id": str(uuid4()),
        "type": "collection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(entries),
        "entry": entries,
        "meta": {
            "tag": [{
                "system": "https://afyasync.health.ke/hie",
                "code": "MEDICATION_REQUEST",
            }]
        },
    }
    assert_valid_bundle(bundle)

    record_audit(
        db,
        action="HIE_MEDICATION_REQUEST_EXPORT",
        resource_type="PRESCRIPTION",
        resource_id=str(prescription.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person.id,
        metadata={"resource_count": len(entries)},
        commit=False,
    )
    return bundle
