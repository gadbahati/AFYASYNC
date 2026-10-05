"""HIE service — robust national-grade exchange packages."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4
from html import escape

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import Allergy, Diagnosis
from app.consent.models import SensitiveDiseaseConsent
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.hie.models import HieExportLog, HieInboundDocument, HieNode
from app.hie.conformance import validate_bundle
from app.hie.terminology_service import canonical_coding
from app.hie.provider_identity import actor_provider_identity_resources
from app.laboratory.models import LabOrder, LabOrderItem, LabResult, LabTest
from app.patients.models import AfyaIdentity, PatientFacility, Person
from app.patients.mpi import _hash_id
from app.pharmacy.models import Medication, Prescription, PrescriptionItem

PURPOSE_OF_USE = {"TREATMENT", "PAYMENT", "PUBLICHEALTH", "OPERATIONS"}


def _require_enrollment(db: Session, patient_id: UUID, facility_id: UUID) -> Person:
    enrolled = db.scalar(
        select(PatientFacility.id).where(
            PatientFacility.patient_id == patient_id,
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
        )
    )
    if enrolled is None:
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    person = db.get(Person, patient_id)
    if person is None or person.status not in {"ACTIVE", "INACTIVE"}:
        raise ValueError("PATIENT_NOT_FOUND")
    return person


def _facility_organization_resource(db: Session, facility_id: UUID) -> dict:
    facility = db.get(Facility, facility_id)
    if facility is None:
        raise ValueError("FACILITY_NOT_FOUND")
    registry = facility.registry_record
    identifiers = []
    if registry and registry.mfl_code:
        identifiers.append({
            "use": "official",
            "type": {"coding": [{"system": "https://fhir.dha.go.ke/fhir/terminology/CodeSystem/facility-identifier-types", "code": "fr-code", "display": "Facility registry code"}]},
            "value": registry.mfl_code,
        })
    if facility.registration_number:
        identifiers.append({
            "use": "secondary",
            "type": {"coding": [{"system": "https://fhir.dha.go.ke/fhir/terminology/CodeSystem/facility-identifier-types", "code": "registration-number", "display": "Facility registration number"}]},
            "value": facility.registration_number,
        })
    if not identifiers:
        raise ValueError("FACILITY_REGISTRY_IDENTIFIER_REQUIRED")
    return {
        "resourceType": "Organization",
        "id": str(facility.id),
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/provider-organization|1.0.0"]},
        "identifier": identifiers,
        "active": facility.status == "ACTIVE",
        "name": facility.name,
        "type": [{"text": "provider", "coding": [{"system": "https://fhir.dha.go.ke/terminology/CodeSystem/OrganizationTypeCS", "code": "provider", "display": "Provider"}]}],
        "address": [{"use": "work", "text": facility.address, "city": facility.sub_county, "district": facility.county}],
        "telecom": ([{"system": "phone", "value": facility.phone, "use": "work"}] if facility.phone else []),
    }


def _normalize_purpose(purpose_of_use: str | None) -> str:
    p = (purpose_of_use or "TREATMENT").strip().upper()
    if p not in PURPOSE_OF_USE:
        raise ValueError("INVALID_PURPOSE_OF_USE")
    return p


def _patient_resource(db: Session, person: Person) -> dict:
    identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person.id))
    identifiers = []
    if identity and identity.status == "ACTIVE":
        identifiers.append(
            {
                "system": "https://afyasync.health.ke/identifier/afya-id",
                "value": identity.afya_id,
            }
        )
    sex = (person.sex or "unknown").strip().lower()
    gender = {"female": "female", "male": "male", "other": "other"}.get(sex, "unknown")
    return {
        "resourceType": "Patient",
        "id": str(person.id),
        "identifier": identifiers,
        "name": [
            {
                "use": "official",
                "family": person.last_name,
                "given": [x for x in [person.first_name, person.middle_name] if x],
            }
        ],
        "birthDate": person.date_of_birth.isoformat() if person.date_of_birth else None,
        "gender": gender,
        "active": person.status == "ACTIVE",
    }


def build_patient_summary_bundle(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
    purpose: str | None = None,
    purpose_of_use: str | None = "TREATMENT",
    destination: str | None = None,
    destination_node_id: UUID | None = None,
    include_labs: bool = True,
) -> dict:
    pou = _normalize_purpose(purpose_of_use)
    person = _require_enrollment(db, patient_id, facility_id)

    if destination_node_id:
        node = db.get(HieNode, destination_node_id)
        if node is None or node.status != "ACTIVE":
            raise ValueError("HIE_NODE_NOT_FOUND")
        if node.facility_id is not None and node.facility_id == facility_id:
            raise ValueError("HIE_DESTINATION_SELF")
        if node.trust_level not in {"HIGH", "NATIONAL"}:
            raise ValueError("HIE_DESTINATION_NOT_TRUSTED")

    entries: list[dict] = []
    redacted = 0

    patient = _patient_resource(db, person)
    entries.append({"fullUrl": f"urn:uuid:{person.id}", "resource": patient})
    facility_resource = _facility_organization_resource(db, facility_id)
    entries.append({"fullUrl": f"urn:uuid:{facility_id}", "resource": facility_resource})

    provider_resources = actor_provider_identity_resources(
        db,
        user_id=actor_user_id,
        facility_id=facility_id,
    )
    for provider_resource in provider_resources:
        entries.append({
            "fullUrl": f"urn:uuid:{provider_resource['resourceType']}/{provider_resource['id']}",
            "resource": provider_resource,
        })
    provider_role = next(
        (r for r in provider_resources if r.get("resourceType") == "PractitionerRole"),
        None,
    )

    allergies = list(
        db.scalars(
            select(Allergy).where(
                Allergy.patient_id == patient_id,
                Allergy.status == "ACTIVE",
            ).limit(50)
        )
    )
    for a in allergies:
        entries.append(
            {
                "fullUrl": f"urn:uuid:{a.id}",
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "id": str(a.id),
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                    "code": {"text": a.allergen},
                    "patient": {"reference": f"Patient/{person.id}"},
                                        "reaction": [{"description": a.reaction}] if getattr(a, "reaction", None) else [],
                },
            }
        )

    encounters = list(
        db.scalars(
            select(Encounter)
            .where(Encounter.patient_id == patient_id)
            .order_by(Encounter.created_at.desc())
            .limit(30)
        )
    )
    for enc in encounters:
        entries.append(
            {
                "fullUrl": f"urn:uuid:{enc.id}",
                "resource": {
                    "resourceType": "Encounter",
                    "id": str(enc.id),
                    "status": (enc.status or "unknown").lower(),
                    "class": {"code": getattr(enc, "encounter_type", None) or "AMB"},
                    "subject": {"reference": f"Patient/{person.id}"},
                    "period": {
                        "start": enc.created_at.isoformat() if enc.created_at else None,
                    },
                    "serviceProvider": {"reference": f"Organization/{enc.facility_id}"},
                },
            }
        )

    diagnoses = list(
        db.scalars(
            select(Diagnosis)
            .join(Encounter, Diagnosis.encounter_id == Encounter.id)
            .where(Diagnosis.encounter_id.in_([enc.id for enc in encounters]))
            .order_by(Diagnosis.created_at.desc(), Diagnosis.id.desc())
            .limit(100)
        )
    )
    for diagnosis in diagnoses:
        consent = db.scalar(
            select(SensitiveDiseaseConsent).where(
                SensitiveDiseaseConsent.diagnosis_id == diagnosis.id,
                SensitiveDiseaseConsent.patient_id == patient_id,
            )
        )
        if consent is not None and not consent.consent_given:
            redacted += 1
            continue
        entries.append(
            {
                "fullUrl": f"urn:uuid:{diagnosis.id}",
                "resource": {
                    "resourceType": "Condition",
                    "id": str(diagnosis.id),
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                    "code": {
                        "coding": ([canonical_coding(db, source_system="AFYASYNC:DIAGNOSIS", source_code=diagnosis.diagnosis_code, display=diagnosis.diagnosis_name)]
                                   if canonical_coding(db, source_system="AFYASYNC:DIAGNOSIS", source_code=diagnosis.diagnosis_code, display=diagnosis.diagnosis_name)
                                   else []),
                        "text": diagnosis.diagnosis_name or diagnosis.diagnosis_code,
                    },
                    "subject": {"reference": f"Patient/{person.id}"},
                    "encounter": {"reference": f"Encounter/{diagnosis.encounter_id}"},
                    "recordedDate": diagnosis.created_at.isoformat() if diagnosis.created_at else None,
                },
            }
        )

    rxs = list(
        db.scalars(
            select(Prescription)
            .where(
                Prescription.patient_id == patient_id,
                Prescription.status.in_(["ACTIVE", "DISPENSED", "PRESCRIBED"]),
            )
            .order_by(Prescription.created_at.desc())
            .limit(30)
        )
    )
    for rx in rxs:
        items = list(
            db.scalars(select(PrescriptionItem).where(PrescriptionItem.prescription_id == rx.id))
        )
        med_texts = []
        for it in items:
            med = db.get(Medication, it.medication_id)
            med_texts.append(
                {
                    "medicationCodeableConcept": ({"coding": [canonical_coding(db, source_system="AFYASYNC:MEDICATION", source_code=med.code if med else None, display=med.name if med else None)]} if canonical_coding(db, source_system="AFYASYNC:MEDICATION", source_code=med.code if med else None, display=med.name if med else None) else {"text": med.name if med else str(it.medication_id)}),
                    "dosageInstruction": [{"text": f"{it.dose} {it.frequency} {it.duration}"}],
                }
            )
        entries.append(
            {
                "fullUrl": f"urn:uuid:{rx.id}",
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": str(rx.id),
                    "status": (rx.status or "unknown").lower(),
                    "intent": "order",
                    "subject": {"reference": f"Patient/{person.id}"},
                    "medicationCodeableConcept": med_texts[0]["medicationCodeableConcept"]
                    if med_texts
                    else {"text": "unknown"},
                    "dosageInstruction": med_texts[0]["dosageInstruction"] if med_texts else [],
                },
            }
        )

    if include_labs:
        lab_orders = list(
            db.scalars(
                select(LabOrder)
                .where(LabOrder.patient_id == patient_id)
                .order_by(LabOrder.created_at.desc())
                .limit(20)
            )
        )
        for order in lab_orders:
            items = list(
                db.scalars(select(LabOrderItem).where(LabOrderItem.lab_order_id == order.id))
            )
            for item in items:
                result = db.scalar(
                    select(LabResult).where(LabResult.lab_order_item_id == item.id)
                )
                if result is None:
                    continue
                test = db.get(LabTest, item.test_id)
                entries.append(
                    {
                        "fullUrl": f"urn:uuid:{result.id}",
                        "resource": {
                            "resourceType": "Observation",
                            "id": str(result.id),
                            "status": (result.status or "final").lower(),
                            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory", "display": "Laboratory"}]}],
                            "code": {
                                "text": test.name if test else "Lab result",
                                "coding": ([canonical_coding(db, source_system="AFYASYNC:LAB_TEST", source_code=test.code, display=test.name)]
                                           if test and canonical_coding(db, source_system="AFYASYNC:LAB_TEST", source_code=test.code, display=test.name)
                                           else []),
                            },
                            "subject": {"reference": f"Patient/{person.id}"},
                            "valueString": result.result,
                            "referenceRange": [{"text": result.reference_range}]
                            if result.reference_range
                            else [],
                            "issued": result.created_at.isoformat() if result.created_at else None,
                            "effectiveDateTime": result.created_at.isoformat() if result.created_at else datetime.now(timezone.utc).isoformat(),
                        },
                    }
                )

    bundle_id = str(uuid4())
    composition_id = f"{bundle_id}-composition"

    section_groups = [
        ("Problems", {"Condition"}),
        ("Allergies", {"AllergyIntolerance"}),
        ("Medications", {"MedicationRequest", "MedicationStatement", "MedicationDispense"}),
        ("Results", {"Observation", "DiagnosticReport"}),
        ("Procedures", {"Procedure"}),
        ("Encounters", {"Encounter"}),
    ]
    sections = []
    for title, resource_types in section_groups:
        refs = [
            {"reference": f"{r.get('resourceType')}/{r.get('id')}"}
            for e in entries
            for r in [e.get("resource")]
            if isinstance(r, dict)
            and r.get("resourceType") in resource_types
            and r.get("id")
        ]
        if refs:
            sections.append({"title": title, "entry": refs})

    composition = {
        "resourceType": "Composition",
        "id": composition_id,
        "meta": {"profile": ["https://fhir.dha.go.ke/kps/StructureDefinition/ke-kps-composition"]},
        "status": "final",
        "type": {"text": "Kenya Patient Summary"},
        "subject": {"reference": f"Patient/{person.id}"},
        "date": datetime.now(timezone.utc).isoformat(),
        "author": (
            [{"reference": f"PractitionerRole/{provider_role['id']}"}]
            if provider_role
            else [{"reference": f"Organization/{facility_id}"}]
        ),
        "title": "Kenya Patient Summary",
        "custodian": {"reference": f"Organization/{facility_id}"},
        "section": sections,
    }
    entries.insert(0, {"fullUrl": f"urn:uuid:{composition_id}", "resource": composition})

    provenance_id = str(uuid4())
    provenance = {
        "resourceType": "Provenance",
        "id": provenance_id,
        "target": [
            {"reference": f"{e['resource']['resourceType']}/{e['resource']['id']}"}
            for e in entries
            if isinstance(e, dict)
            and isinstance(e.get("resource"), dict)
            and e["resource"].get("resourceType")
            and e["resource"].get("id")
        ],
        "recorded": datetime.now(timezone.utc).isoformat(),
        "agent": [{
            "type": {"text": "author"},
            "who": {
                "reference": (
                    f"PractitionerRole/{provider_role['id']}"
                    if provider_role
                    else f"Organization/{facility_id}"
                )
            },
            "onBehalfOf": {"reference": f"Organization/{facility_id}"},
        }],
        "activity": {"text": "HIE patient summary export"},
        "reason": [{"text": "National health information exchange"}],
    }
    entries.insert(1, {"fullUrl": f"urn:uuid:{provenance_id}", "resource": provenance})

    bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "document",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(entries),
        "entry": entries,
        "meta": {
            "tag": [
                {"system": "https://afyasync.health.ke/hie", "code": "PATIENT_SUMMARY"},
                {"system": "https://afyasync.health.ke/purpose-of-use", "code": pou},
                {"system": "https://afyasync.health.ke/developer", "code": "BAHATI_GAD_WANGWE"},
            ],
            "security": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-Confidentiality",
                    "code": "R" if redacted else "N",
                }
            ],
        },
    }

    conformance_errors = validate_bundle(bundle, require_patient=True, require_provenance=True)
    if conformance_errors:
        raise ValueError("HIE_FHIR_CONFORMANCE_FAILED:" + ",".join(conformance_errors))

    log = HieExportLog(
        facility_id=facility_id,
        patient_id=patient_id,
        export_type="PATIENT_SUMMARY",
        resource_count=len(entries),
        actor_user_id=actor_user_id,
        purpose=(purpose or "care-coordination")[:200],
        purpose_of_use=pou,
        destination=(destination or "")[:200] or None,
        destination_node_id=destination_node_id,
        status="SUCCESS",
        redacted_sensitive=redacted,
    )
    db.add(log)
    db.flush()

    record_audit(
        db,
        action="HIE_PATIENT_SUMMARY_EXPORT",
        resource_type="PERSON",
        resource_id=str(patient_id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={
            "bundle_id": bundle_id,
            "resources": len(entries),
            "purpose_of_use": pou,
            "redacted_sensitive": redacted,
            "destination": destination,
        },
        commit=False,
    )
    return bundle


def build_referral_package(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    encounter_id: UUID | None = None,
    clinical_summary: str | None = None,
    actor_user_id: UUID | None = None,
    destination: str | None = None,
    destination_node_id: UUID | None = None,
    purpose_of_use: str | None = "TREATMENT",
) -> dict:
    summary = build_patient_summary_bundle(
        db,
        patient_id=patient_id,
        facility_id=facility_id,
        actor_user_id=actor_user_id,
        purpose="referral",
        purpose_of_use=purpose_of_use,
        destination=destination,
        destination_node_id=destination_node_id,
        include_labs=True,
    )
    last = db.scalar(
        select(HieExportLog)
        .where(
            HieExportLog.facility_id == facility_id,
            HieExportLog.patient_id == patient_id,
        )
        .order_by(HieExportLog.created_at.desc())
        .limit(1)
    )
    if last:
        last.export_type = "REFERRAL_PACKAGE"
        last.notes = (clinical_summary or "")[:2000] or None
        if encounter_id:
            last.notes = ((last.notes or "") + f" encounter={encounter_id}")[:2000]

    summary["meta"]["tag"] = [
        {"system": "https://afyasync.health.ke/hie", "code": "REFERRAL_PACKAGE"},
        {
            "system": "https://afyasync.health.ke/purpose-of-use",
            "code": _normalize_purpose(purpose_of_use),
        },
        {"system": "https://afyasync.health.ke/developer", "code": "BAHATI_GAD_WANGWE"},
    ]
    if clinical_summary:
        composition = next(
            (e["resource"] for e in summary["entry"] if isinstance(e, dict) and isinstance(e.get("resource"), dict) and e["resource"].get("resourceType") == "Composition"),
            None,
        )
        if composition is not None:
            composition["title"] = "AfyaSync Referral Package"
            composition["type"] = {"text": "Referral note"}
            composition["section"].insert(
                0,
                {"title": "Clinical summary", "text": {"status": "generated", "div": f"<div>{escape(clinical_summary[:4000])}</div>"}},
            )
            summary["total"] = len(summary["entry"])
    return summary


def validate_inbound_bundle(
    db: Session,
    *,
    facility_id: UUID,
    payload: dict,
    source_code: str | None = None,
    source_node_id: UUID | None = None,
    actor_user_id: UUID | None = None,
) -> dict:
    errors = validate_bundle(payload)
    btype = payload.get("type")
    entries = payload.get("entry") or []


    patient_id = None
    has_patient = False
    inbound_patient = None
    for e in entries[:200]:
        if not isinstance(e, dict):
            errors.append("BAD_ENTRY")
            continue
        res = e.get("resource") or {}
        if res.get("resourceType") == "Patient":
            has_patient = True
            inbound_patient = res
    if not has_patient:
        errors.append("MISSING_PATIENT_RESOURCE")

    if source_node_id is None:
        errors.append("SOURCE_NODE_REQUIRED")
        node = None
    else:
        node = db.get(HieNode, source_node_id)
        if node is None or node.status != "ACTIVE":
            errors.append("UNKNOWN_SOURCE_NODE")
        else:
            if node.trust_level not in {"HIGH", "NATIONAL"}:
                errors.append("UNTRUSTED_SOURCE_NODE")
            if source_code and source_code.strip().upper() != node.code:
                errors.append("SOURCE_CODE_MISMATCH")
            if node.facility_id is not None and node.facility_id == facility_id:
                errors.append("SOURCE_NODE_SELF")

    doc_type = "UNKNOWN"
    tags = (payload.get("meta") or {}).get("tag") or []
    for t in tags:
        if isinstance(t, dict) and t.get("code") in {"PATIENT_SUMMARY", "REFERRAL_PACKAGE"}:
            doc_type = t["code"]
            break

    # A national KPS patient summary is accepted only as the verified KPS
    # document shape; generic FHIR documents must not masquerade as KPS.
    if doc_type == "PATIENT_SUMMARY":
        if payload.get("type") != "document":
            errors.append("KPS_PATIENT_SUMMARY_MUST_BE_DOCUMENT")
        first_resource = (
            (entries[0].get("resource") if isinstance(entries[0], dict) else None)
            if entries
            else None
        )
        if not isinstance(first_resource, dict) or first_resource.get("resourceType") != "Composition":
            errors.append("KPS_COMPOSITION_MUST_BE_FIRST")
        else:
            profile = ((first_resource.get("meta") or {}).get("profile") or [])
            if "https://fhir.dha.go.ke/kps/StructureDefinition/ke-kps-composition" not in profile:
                errors.append("KPS_COMPOSITION_PROFILE_REQUIRED")
            if first_resource.get("status") != "final":
                errors.append("KPS_COMPOSITION_FINAL_REQUIRED")
            sections = first_resource.get("section")
            if not sections:
                errors.append("KPS_COMPOSITION_SECTIONS_REQUIRED")
            elif not any(isinstance(section, dict) and section.get("entry") for section in sections):
                errors.append("KPS_COMPOSITION_SECTION_ENTRY_REQUIRED")

    # KPS-specific checks above must participate in the final acceptance decision.
    status = "REJECTED" if errors else "ACCEPTED"

    # FHIR Bundle ids are the durable inbound message identity. Replaying the
    # same accepted Bundle from the same trusted source must be idempotent and
    # must not create a second clinical import opportunity.
    bundle_id = str(payload.get("id") or "").strip()[:80] or None
    if status == "ACCEPTED" and source_node_id is not None and bundle_id is not None:
        existing = db.scalar(
            select(HieInboundDocument).where(
                HieInboundDocument.source_node_id == source_node_id,
                HieInboundDocument.bundle_id == bundle_id,
            )
        )
        if existing is not None:
            record_audit(
                db,
                action="HIE_INBOUND_DOCUMENT_REPLAY",
                resource_type="HIE_INBOUND",
                resource_id=str(existing.id),
                result="IDEMPOTENT_REPLAY",
                user_id=actor_user_id,
                facility_id=facility_id,
                patient_id=existing.patient_id,
                metadata={"bundle_id": bundle_id, "source_node_id": str(source_node_id)},
                commit=False,
            )
            return {
                "id": str(existing.id),
                "validation_status": existing.validation_status,
                "errors": existing.validation_errors or [],
                "document_type": existing.document_type,
                "resource_count": existing.resource_count,
                "patient_id": str(existing.patient_id) if existing.patient_id else None,
                "idempotent_replay": True,
                "match_status": existing.match_status,
            }

    row = HieInboundDocument(
        facility_id=facility_id,
        patient_id=patient_id,
        source_node_id=source_node_id,
        source_code=(source_code or "")[:80] or None,
        bundle_id=bundle_id,
        document_type=doc_type,
        resource_count=len(entries) if isinstance(entries, list) else 0,
        validation_status=status,
        validation_errors=errors or None,
        payload=payload,
        payload_meta={
            "type": btype,
            "total": payload.get("total"),
            "timestamp": payload.get("timestamp"),
        },
        received_by=actor_user_id,
        match_status="UNRESOLVED" if not errors else "REJECTED",
    )
    db.add(row)
    db.flush()

    record_audit(
        db,
        action="HIE_INBOUND_DOCUMENT",
        resource_type="HIE_INBOUND",
        resource_id=str(row.id),
        result=status,
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={"errors": errors, "document_type": doc_type},
        commit=False,
    )

    return {
        "id": str(row.id),
        "validation_status": status,
        "errors": errors,
        "document_type": doc_type,
        "resource_count": row.resource_count,
        "patient_id": str(patient_id) if patient_id else None,
    }

def _inbound_patient_identifiers(resource: dict) -> dict:
    result = {}
    for item in resource.get("identifier") or []:
        if not isinstance(item, dict):
            continue
        system = str(item.get("system") or "").lower()
        value = str(item.get("value") or "").strip()
        if not value:
            continue
        if "afya-id" in system:
            result["afya_id"] = value
        elif "national" in system or "national-id" in system:
            result["national_id"] = value
        elif "phone" in system:
            result["phone"] = value
    return result

def resolve_inbound_patient(db: Session, *, inbound_id: UUID, facility_id: UUID, actor_user_id: UUID | None = None) -> dict:
    row = db.get(HieInboundDocument, inbound_id)
    if row is None or row.facility_id != facility_id:
        raise ValueError("INBOUND_DOCUMENT_NOT_FOUND")
    if row.validation_status != "ACCEPTED":
        raise ValueError("INBOUND_DOCUMENT_NOT_ACCEPTED")
    entries = row.payload.get("entry", []) if row.payload else []
    patient_resource = next((e.get("resource") for e in entries if isinstance(e, dict) and isinstance(e.get("resource"), dict) and e["resource"].get("resourceType") == "Patient"), None)
    if not patient_resource:
        raise ValueError("MISSING_PATIENT_RESOURCE")
    # Never turn an identity match into a local match without an active facility enrollment.
    # Enrollment is re-checked at import time as well, so queued/previously matched records cannot bypass it.
    ids = _inbound_patient_identifiers(patient_resource)
    candidates = {}
    if ids.get("afya_id"):
        identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.afya_id == ids["afya_id"], AfyaIdentity.status == "ACTIVE"))
        if identity:
            person = db.get(Person, identity.person_id)
            if person:
                candidates[person.id] = (person, identity, ["AFYA_ID"])
    if ids.get("national_id"):
        person = db.scalar(select(Person).where(Person.national_id_hash == _hash_id(ids["national_id"]), Person.status == "ACTIVE"))
        if person:
            identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person.id, AfyaIdentity.status == "ACTIVE"))
            if identity:
                candidates.setdefault(person.id, (person, identity, ["NATIONAL_ID"]))
    names = patient_resource.get("name") or []
    official = next((n for n in names if isinstance(n, dict) and n.get("use") == "official"), names[0] if names else {})
    given = official.get("given") or []
    first = str(given[0]).strip() if given else ""
    last = str(official.get("family") or "").strip()
    dob = None
    if patient_resource.get("birthDate"):
        try:
            from datetime import date
            dob = date.fromisoformat(str(patient_resource["birthDate"])[:10])
        except ValueError:
            pass
    phone = ids.get("phone")
    if first and last and dob:
        stmt = select(Person, AfyaIdentity).join(AfyaIdentity, AfyaIdentity.person_id == Person.id).where(Person.status == "ACTIVE", Person.first_name.ilike(first), Person.last_name.ilike(last), Person.date_of_birth == dob, AfyaIdentity.status == "ACTIVE")
        if phone:
            stmt = stmt.where(Person.phone == phone)
        for person, identity in db.execute(stmt.limit(10)).all():
            reasons = ["FIRST_NAME", "LAST_NAME", "DATE_OF_BIRTH"]
            if phone and person.phone == phone:
                reasons.append("PHONE")
            candidates.setdefault(person.id, (person, identity, reasons))
    if len(candidates) == 1:
        person, identity, reasons = next(iter(candidates.values()))
        if row.document_type == "PATIENT_SUMMARY":
            composition = next((e.get("resource") for e in entries if isinstance(e, dict) and isinstance(e.get("resource"), dict) and e["resource"].get("resourceType") == "Composition"), None)
            subject_ref = ((composition or {}).get("subject") or {}).get("reference")
            if subject_ref and subject_ref != f"Patient/{person.id}":
                row.match_status = "UNMATCHED"
                row.match_reasons = ["KPS_COMPOSITION_PATIENT_MISMATCH"]
                record_audit(db, action="HIE_INBOUND_MPI_UNRESOLVED", resource_type="HIE_INBOUND", resource_id=str(row.id), result="UNMATCHED", user_id=actor_user_id, facility_id=facility_id, metadata={"reason": row.match_reasons, "subject": subject_ref}, commit=False)
                return {"status": "UNMATCHED", "patient_id": None, "candidate_count": 1, "match_reasons": row.match_reasons}
        enrolled = db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id == person.id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE"))
        if enrolled is None:
            row.match_status = "UNMATCHED"
            row.match_reasons = ["PATIENT_NOT_ENROLLED_AT_FACILITY"]
            record_audit(db, action="HIE_INBOUND_MPI_UNRESOLVED", resource_type="HIE_INBOUND", resource_id=str(row.id), result="UNMATCHED", user_id=actor_user_id, facility_id=facility_id, metadata={"reason": row.match_reasons}, commit=False)
            return {"status": "UNMATCHED", "patient_id": None, "candidate_count": 1, "match_reasons": row.match_reasons}
        row.patient_id = person.id
        row.match_status = "MATCHED"
        row.match_reasons = reasons
        row.matched_at = datetime.now(timezone.utc)
        record_audit(db, action="HIE_INBOUND_MPI_MATCH", resource_type="HIE_INBOUND", resource_id=str(row.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=person.id, metadata={"match_reasons": reasons, "afya_id": identity.afya_id}, commit=False)
        return {"status": "MATCHED", "patient_id": str(person.id), "afya_id": identity.afya_id, "match_reasons": reasons}
    row.match_status = "AMBIGUOUS" if len(candidates) > 1 else "UNMATCHED"
    row.match_reasons = ["MULTIPLE_CANDIDATES"] if len(candidates) > 1 else ["NO_SAFE_MATCH"]
    record_audit(db, action="HIE_INBOUND_MPI_UNRESOLVED", resource_type="HIE_INBOUND", resource_id=str(row.id), result=row.match_status, user_id=actor_user_id, facility_id=facility_id, metadata={"candidate_count": len(candidates), "reason": row.match_reasons}, commit=False)
    return {"status": row.match_status, "patient_id": None, "candidate_count": len(candidates), "match_reasons": row.match_reasons}

def upsert_node(db: Session, *, data: dict, facility_id: UUID) -> HieNode:
    code = (data.get("code") or "").strip().upper()
    if not code:
        raise ValueError("NODE_CODE_REQUIRED")
    row = db.scalar(select(HieNode).where(HieNode.code == code))
    requested_facility_id = data.get("facility_id")
    if requested_facility_id is not None:
        try:
            requested_facility_id = UUID(str(requested_facility_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("HIE_NODE_FACILITY_INVALID") from exc
        if requested_facility_id != facility_id:
            raise ValueError("HIE_NODE_FACILITY_ACCESS_DENIED")
    if row is not None and row.facility_id is not None and row.facility_id != facility_id:
        raise ValueError("HIE_NODE_ACCESS_DENIED")
    is_new = row is None
    if is_new:
        row = HieNode(code=code)
        db.add(row)
    row.name = (data.get("name") or code)[:200]
    row.node_type = (data.get("node_type") or "FACILITY")[:40]
    row.endpoint_url = data.get("endpoint_url")
    row.facility_id = facility_id
    if is_new:
        row.trust_level = "STANDARD"
    elif row.trust_level not in {"HIGH", "NATIONAL"}:
        row.trust_level = "STANDARD"
    row.status = "ACTIVE"
    db.flush()
    return row


def list_nodes(db: Session, *, facility_id: UUID, active_only: bool = True) -> list[HieNode]:
    q = select(HieNode).where(
        (HieNode.facility_id == facility_id) | (HieNode.trust_level == "NATIONAL")
    ).order_by(HieNode.name)
    if active_only:
        q = q.where(HieNode.status == "ACTIVE")
    return list(db.scalars(q.limit(200)))


def list_export_logs(db: Session, facility_id: UUID, *, limit: int = 50) -> list[HieExportLog]:
    limit = min(max(limit, 1), 200)
    return list(
        db.scalars(
            select(HieExportLog)
            .where(HieExportLog.facility_id == facility_id)
            .order_by(HieExportLog.created_at.desc())
            .limit(limit)
        )
    )


def capability_statement() -> dict:
    return {
        "resourceType": "CapabilityStatement",
        "id": "afyasync-hie",
        "status": "active",
        "kind": "instance",
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json", "application/json"],
        "implementation": {
            "description": "AfyaSync national health operating platform HIE interface",
            "url": "https://afyasync.health.ke/api/v1/hie",
        },
        "rest": [
            {
                "mode": "server",
                "resource": [
                    {"type": "Patient", "interaction": [{"code": "read"}, {"code": "search-type"}], "operation": [{"name": "$match", "definition": "Patient/$match"}]},
                    {"type": "AllergyIntolerance", "interaction": [{"code": "search-type"}]},
                    {"type": "Encounter", "interaction": [{"code": "search-type"}]},
                    {"type": "MedicationRequest", "interaction": [{"code": "search-type"}]},
                    {"type": "MedicationStatement", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "Observation", "interaction": [{"code": "search-type"}]},
                    {"type": "Condition", "interaction": [{"code": "search-type"}]},
                    {"type": "ServiceRequest", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "Task", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "Communication", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "CommunicationRequest", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "Consent", "interaction": [{"code": "read"}, {"code": "search-type"}]},
                    {"type": "Bundle", "interaction": [{"code": "create"}, {"code": "read"}]},
                    {"type": "Composition", "interaction": [{"code": "read"}]},
                ],
                "operation": [
                    {"name": "summary", "definition": "Patient/$summary"},
                    {"name": "referral-package", "definition": "HIE referral document"},
                ],
            }
        ],
        "meta": {
            "tag": [
                {"system": "https://afyasync.health.ke/developer", "code": "BAHATI_GAD_WANGWE"}
            ]
        },
    }

SUPPORTED_INBOUND_RESOURCE_TYPES = {
    "Condition",
    "Observation",
    "AllergyIntolerance",
    "MedicationRequest",
    "MedicationStatement",
    "Encounter",
    "DiagnosticReport",
    "DocumentReference",
    "Composition",
    "Provenance",
}


def _bundle_purpose_of_use(payload: dict) -> str:
    for tag in (payload.get("meta") or {}).get("tag") or []:
        if not isinstance(tag, dict):
            continue
        system = str(tag.get("system") or "").lower()
        code = str(tag.get("code") or "").strip().upper()
        if "purpose-of-use" in system and code in PURPOSE_OF_USE:
            return code
    return "TREATMENT"


def _parse_effective_at(resource: dict) -> datetime | None:
    for key in ("effectiveDateTime", "issued", "recordedDate", "authoredOn"):
        value = resource.get(key)
        if not value:
            continue
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    period = resource.get("period")
    if isinstance(period, dict):
        value = period.get("start") or period.get("end")
        if value:
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                pass
    return None


def _resource_code_and_text(resource: dict) -> tuple[str | None, str | None]:
    codeable = resource.get("code") or resource.get("medicationCodeableConcept") or {}
    codings = codeable.get("coding") if isinstance(codeable, dict) else None
    code = None
    if isinstance(codings, list):
        for coding in codings:
            if isinstance(coding, dict) and coding.get("code"):
                code = str(coding["code"])[:100]
                break
    text = codeable.get("text") if isinstance(codeable, dict) else None
    if text is None:
        text = resource.get("description") or resource.get("title")
    return code, str(text)[:4000] if text is not None else None


def _inbound_consent_allows_sensitive(payload: dict, patient_id: UUID, purpose: str) -> bool:
    for entry in payload.get("entry") or []:
        resource = entry.get("resource") if isinstance(entry, dict) else None
        if not isinstance(resource, dict) or resource.get("resourceType") != "Consent":
            continue
        subject = resource.get("patient") or resource.get("subject") or {}
        reference = subject.get("reference") if isinstance(subject, dict) else None
        if reference and str(reference).split("/")[-1] != str(patient_id):
            continue
        provision = resource.get("provision") or {}
        if str(provision.get("type") or "").lower() != "permit":
            continue
        purposes = provision.get("purpose") or []
        if not purposes:
            return True
        for item in purposes:
            if not isinstance(item, dict):
                continue
            if str(item.get("code") or "").upper() == purpose:
                return True
            for coding in item.get("coding") or []:
                if isinstance(coding, dict) and str(coding.get("code") or "").upper() == purpose:
                    return True
    return False


def import_inbound_clinical_resources(
    db: Session,
    *,
    inbound_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    row = db.get(HieInboundDocument, inbound_id)
    if row is None or row.facility_id != facility_id:
        raise ValueError("INBOUND_DOCUMENT_NOT_FOUND")
    if row.validation_status != "ACCEPTED":
        raise ValueError("INBOUND_DOCUMENT_NOT_ACCEPTED")
    if row.match_status != "MATCHED" or row.patient_id is None:
        raise ValueError("INBOUND_PATIENT_NOT_MATCHED")

    _require_enrollment(db, row.patient_id, facility_id)

    node = db.get(HieNode, row.source_node_id) if row.source_node_id else None
    if node is None or node.status != "ACTIVE" or node.trust_level not in {"HIGH", "NATIONAL"}:
        raise ValueError("INBOUND_SOURCE_NOT_TRUSTED")

    from app.consent.models import SensitiveCategory
    from app.hie.import_models import HieImportedResource

    purpose = _bundle_purpose_of_use(row.payload or {})
    payload_patient_refs = []
    for entry in (row.payload or {}).get("entry") or []:
        resource = entry.get("resource") if isinstance(entry, dict) else None
        if not isinstance(resource, dict) or resource.get("resourceType") != "Patient":
            continue
        payload_patient_refs.append(str(resource.get("id") or "").strip())
    if payload_patient_refs and all(ref != str(row.patient_id) for ref in payload_patient_refs):
        raise ValueError("INBOUND_PATIENT_IDENTITY_MISMATCH")
    sensitive_codes = {
        str(code).strip().upper()
        for code in db.scalars(
            select(SensitiveCategory.code).where(SensitiveCategory.is_active.is_(True))
        )
        if code
    }
    consent_allows_sensitive = _inbound_consent_allows_sensitive(
        row.payload or {}, row.patient_id, purpose
    )

    imported = []
    duplicates = []
    blocked = []
    skipped = []

    for entry in (row.payload or {}).get("entry") or []:
        resource = entry.get("resource") if isinstance(entry, dict) else None
        if not isinstance(resource, dict):
            continue
        resource_type = str(resource.get("resourceType") or "")
        if resource_type in {"Patient", "Consent"}:
            continue
        if resource_type not in SUPPORTED_INBOUND_RESOURCE_TYPES:
            skipped.append(resource_type or "UNKNOWN")
            continue

        remote_id = str(resource.get("id") or "").strip()
        if not remote_id:
            skipped.append(f"{resource_type}:MISSING_ID")
            continue

        existing = db.scalar(
            select(HieImportedResource).where(
                HieImportedResource.source_node_id == row.source_node_id,
                HieImportedResource.resource_type == resource_type,
                HieImportedResource.remote_resource_id == remote_id,
            )
        )
        if existing is not None:
            duplicates.append(str(existing.id))
            continue

        normalized_code, normalized_text = _resource_code_and_text(resource)
        sensitivity = "NORMAL"
        if resource_type == "Condition" and normalized_code and normalized_code.upper() in sensitive_codes:
            sensitivity = "SENSITIVE"
            if not consent_allows_sensitive:
                blocked.append(remote_id)
                continue

        imported_row = HieImportedResource(
            inbound_document_id=row.id,
            facility_id=facility_id,
            patient_id=row.patient_id,
            source_node_id=row.source_node_id,
            resource_type=resource_type,
            remote_resource_id=remote_id,
            status="IMPORTED",
            purpose_of_use=purpose,
            sensitivity=sensitivity,
            normalized_code=normalized_code,
            normalized_text=normalized_text,
            effective_at=_parse_effective_at(resource),
            source_provenance={
                "source_node_id": str(row.source_node_id),
                "source_code": row.source_code,
                "bundle_id": row.bundle_id,
                "inbound_document_id": str(row.id),
                "remote_resource_id": remote_id,
            },
            payload=resource,
            imported_by=actor_user_id,
        )
        db.add(imported_row)
        db.flush()
        imported.append({
            "id": str(imported_row.id),
            "resource_type": resource_type,
            "remote_resource_id": remote_id,
            "sensitivity": sensitivity,
        })

    result = {
        "inbound_id": str(row.id),
        "patient_id": str(row.patient_id),
        "purpose_of_use": purpose,
        "imported_count": len(imported),
        "duplicate_count": len(duplicates),
        "blocked_sensitive_count": len(blocked),
        "skipped_count": len(skipped),
        "imported": imported,
        "duplicates": duplicates,
        "blocked_sensitive": blocked,
        "skipped": skipped,
    }
    record_audit(
        db,
        action="HIE_INBOUND_CLINICAL_IMPORT",
        resource_type="HIE_INBOUND",
        resource_id=str(row.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=row.patient_id,
        metadata={
            "purpose_of_use": purpose,
            "imported_count": len(imported),
            "duplicate_count": len(duplicates),
            "blocked_sensitive_count": len(blocked),
            "skipped_count": len(skipped),
        },
        commit=False,
    )
    return result


def list_imported_patient_resources(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    limit: int = 100,
) -> list:
    from app.hie.import_models import HieImportedResource

    limit = min(max(limit, 1), 200)
    return list(
        db.scalars(
            select(HieImportedResource)
            .where(
                HieImportedResource.patient_id == patient_id,
                HieImportedResource.facility_id == facility_id,
                HieImportedResource.status == "IMPORTED",
            )
            .order_by(
                HieImportedResource.effective_at.desc().nullslast(),
                HieImportedResource.imported_at.desc(),
            )
            .limit(limit)
        )
    )
