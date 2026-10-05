"""FHIR MedicationStatement interoperability for existing AfyaSync prescriptions."""
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


class MedicationStatementFhirError(ValueError):
    pass


STATUS_MAP = {
    "ACTIVE": "active",
    "DISPENSED": "completed",
    "CANCELLED": "stopped",
}


def build_medication_statement_bundle(
    db: Session,
    *,
    prescription_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise MedicationStatementFhirError("PRESCRIPTION_NOT_FOUND")

    encounter = db.get(Encounter, prescription.encounter_id)
    if encounter is None:
        raise MedicationStatementFhirError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise MedicationStatementFhirError("ACCESS_DENIED")

    person = db.get(Person, prescription.patient_id)
    if person is None:
        raise MedicationStatementFhirError("PATIENT_NOT_FOUND")

    facility = db.get(Facility, facility_id)
    if facility is None:
        raise MedicationStatementFhirError("FACILITY_NOT_FOUND")

    prescriber = db.get(Staff, prescription.prescribed_by)
    if prescriber is None or prescriber.facility_id != facility_id or prescriber.status != "ACTIVE":
        raise MedicationStatementFhirError("PRESCRIBER_NOT_FOUND")

    items = list(
        db.scalars(
            select(PrescriptionItem)
            .where(PrescriptionItem.prescription_id == prescription.id)
            .order_by(PrescriptionItem.id)
        )
    )
    if not items:
        raise MedicationStatementFhirError("PRESCRIPTION_ITEMS_REQUIRED")

    patient = _patient_resource(db, person)
    organization = _facility_organization_resource(db, facility_id)
    providers = provider_identity_resources(db, facility_id=facility_id, staff_id=prescriber.id)

    resources = [
        {"fullUrl": f"urn:uuid:{patient['id']}", "resource": patient},
        {"fullUrl": f"urn:uuid:{organization['id']}", "resource": organization},
    ]
    resources.extend({"fullUrl": f"urn:uuid:{r['id']}", "resource": r} for r in providers)

    status = STATUS_MAP.get(prescription.status, "active")
    for item in items:
        medication = db.get(Medication, item.medication_id)
        if medication is None or medication.status != "ACTIVE":
            raise MedicationStatementFhirError("MEDICATION_NOT_ACTIVE")

        coding = canonical_coding(
            db,
            source_system="AFYASYNC:MEDICATION",
            source_code=medication.code,
            display=medication.name,
        )
        if coding is None:
            raise MedicationStatementFhirError(
                f"MEDICATION_CODE_NOT_NATIONALLY_MAPPED:{medication.code}"
            )

        statement = {
            "resourceType": "MedicationStatement",
            "id": str(item.id),
            "status": status,
            "medicationCodeableConcept": {"coding": [coding], "text": medication.name},
            "subject": {"reference": f"Patient/{person.id}"},
            "context": {"reference": f"Encounter/{encounter.id}"},
            "effectiveDateTime": (
                prescription.created_at or datetime.now(timezone.utc)
            ).isoformat(),
            "dateAsserted": (
                prescription.created_at or datetime.now(timezone.utc)
            ).isoformat(),
            "informationSource": {"reference": f"Practitioner/{prescriber.id}"},
            "dosage": [{
                "text": " ".join(
                    value for value in (
                        item.dose,
                        item.frequency,
                        item.route,
                        item.duration,
                        item.instructions,
                    ) if value
                )
            }],
        }
        if item.quantity is not None:
            statement["dosage"][0]["doseAndRate"] = [{
                "doseQuantity": {
                    "value": float(item.quantity),
                    **({"unit": medication.unit} if medication.unit else {}),
                }
            }]

        resources.append({
            "fullUrl": f"urn:uuid:{statement['id']}",
            "resource": statement,
        })

    provenance = {
        "resourceType": "Provenance",
        "id": str(uuid4()),
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"
            ]
        },
        "target": [
            {"reference": f"MedicationStatement/{item.id}"} for item in items
        ],
        "recorded": datetime.now(timezone.utc).isoformat(),
        "agent": [{"who": {"reference": f"Organization/{facility_id}"}}],
    }
    resources.append({
        "fullUrl": f"urn:uuid:{provenance['id']}",
        "resource": provenance,
    })

    bundle = {
        "resourceType": "Bundle",
        "id": f"medication-statements-{uuid4()}",
        "type": "collection",
        "entry": resources,
    }
    assert_valid_bundle(bundle)

    record_audit(
        db,
        action="HIE_MEDICATION_STATEMENT_EXPORT",
        resource_type="MEDICATION_STATEMENT",
        resource_id=str(prescription.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=prescription.patient_id,
        metadata={"item_count": len(items), "status": status},
        commit=False,
    )
    return bundle
