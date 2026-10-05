"""FHIR MedicationDispense interoperability for completed pharmacy dispensing.

Projects persisted AfyaSync prescriptions and medication items without inventing
Kenya national profiles or medication codes. National medication coding is
accepted only through the verified terminology registry.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.hie.terminology_service import canonical_coding
from app.patients.models import Person
from app.pharmacy.models import Medication, Prescription, PrescriptionItem
from app.rbac.models import Staff


class MedicationDispenseFhirError(ValueError):
    pass


_STATUS_MAP = {
    "ACTIVE": "in-progress",
    "DISPENSED": "completed",
    "CANCELLED": "cancelled",
}


def build_medication_dispense_bundle(
    db: Session,
    *,
    prescription_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise MedicationDispenseFhirError("PRESCRIPTION_NOT_FOUND")

    encounter = db.get(Encounter, prescription.encounter_id)
    if encounter is None:
        raise MedicationDispenseFhirError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise MedicationDispenseFhirError("ACCESS_DENIED")
    if encounter.patient_id != prescription.patient_id:
        raise MedicationDispenseFhirError("PATIENT_CONTEXT_MISMATCH")

    person = db.get(Person, prescription.patient_id)
    if person is None:
        raise MedicationDispenseFhirError("PATIENT_NOT_FOUND")

    prescriber = db.get(Staff, prescription.prescribed_by)
    if prescriber is None or prescriber.facility_id != facility_id or prescriber.status != "ACTIVE":
        raise MedicationDispenseFhirError("PRESCRIBER_NOT_FOUND")

    items = list(db.scalars(
        select(PrescriptionItem)
        .where(PrescriptionItem.prescription_id == prescription.id)
    ).all())
    if not items:
        raise MedicationDispenseFhirError("PRESCRIPTION_EMPTY")

    status = _STATUS_MAP.get((prescription.status or "").upper())
    if status is None:
        raise MedicationDispenseFhirError(
            f"UNSUPPORTED_PRESCRIPTION_STATUS:{prescription.status}"
        )

    patient = _patient_resource(db, person)
    patient["meta"] = {
        "profile": [
            "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"
        ]
    }
    organization = _facility_organization_resource(db, facility_id)
    providers = provider_identity_resources(
        db, facility_id=facility_id, staff_id=prescriber.id
    )
    role = next(
        (r for r in providers if r.get("resourceType") == "PractitionerRole"),
        None,
    )
    prescriber_ref = (
        f"PractitionerRole/{role['id']}"
        if role
        else f"Organization/{facility_id}"
    )

    resources = [patient, organization, *providers]
    dispense_ids: list[str] = []

    for item in items:
        medication = db.get(Medication, item.medication_id)
        if medication is None or medication.status != "ACTIVE":
            raise MedicationDispenseFhirError("MEDICATION_NOT_FOUND")

        coding = canonical_coding(
            db,
            source_system="AFYASYNC:MEDICATION",
            source_code=medication.code,
            display=medication.name,
        )
        if coding is None:
            raise MedicationDispenseFhirError(
                f"MEDICATION_CODE_NOT_MAPPED:{medication.code}"
            )

        dispense_id = str(uuid4())
        dispense_ids.append(dispense_id)
        quantity = {"value": float(item.quantity)}
        if medication.unit:
            quantity["unit"] = medication.unit

        dispense = {
            "resourceType": "MedicationDispense",
            "id": dispense_id,
            "status": status,
            "medicationCodeableConcept": {
                "coding": [coding],
                "text": medication.name,
            },
            "subject": {"reference": f"Patient/{person.id}"},
            "context": {"reference": f"Encounter/{encounter.id}"},
            "authorizingPrescription": [
                {"reference": f"MedicationRequest/{prescription.id}"}
            ],
            "quantity": quantity,
            "performer": [{"actor": {"reference": prescriber_ref}}],
            "whenHandedOver": (
                prescription.created_at.astimezone(timezone.utc).isoformat()
                if prescription.created_at else datetime.now(timezone.utc).isoformat()
            ),
            "dosageInstruction": [{
                "text": " ".join(
                    p for p in [
                        item.dose,
                        item.frequency,
                        item.duration,
                        item.route,
                        item.instructions,
                    ] if p
                )
            }],
        }
        resources.append(dispense)

    provenance = {
        "resourceType": "Provenance",
        "id": str(uuid4()),
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"
            ]
        },
        "target": [{"reference": f"MedicationDispense/{rid}"} for rid in dispense_ids],
        "recorded": datetime.now(timezone.utc).isoformat(),
        "agent": [{
            "type": {"text": "prescriber"},
            "who": {"reference": prescriber_ref},
            "onBehalfOf": {"reference": f"Organization/{facility_id}"},
        }],
        "activity": {"text": "HIE medication dispense export"},
    }
    resources.append(provenance)

    bundle = {
        "resourceType": "Bundle",
        "id": f"medication-dispense-{prescription.id}",
        "type": "collection",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(resources),
        "entry": [
            {
                "fullUrl": f"urn:uuid:{resource['resourceType']}/{resource['id']}",
                "resource": resource,
            }
            for resource in resources
        ],
    }
    try:
        assert_valid_bundle(bundle)
    except ValueError as exc:
        raise MedicationDispenseFhirError(str(exc)) from exc

    record_audit(
        db,
        action="HIE_MEDICATION_DISPENSE_EXPORT",
        resource_type="PRESCRIPTION",
        resource_id=str(prescription.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person.id,
        metadata={"resource_count": len(resources), "item_count": len(items)},
        commit=False,
    )
    return bundle
