"""HIE service — robust national-grade exchange packages."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import Allergy
from app.encounters.models import Encounter
from app.hie.models import HieExportLog, HieInboundDocument, HieNode
from app.laboratory.models import LabOrder, LabOrderItem, LabResult, LabTest
from app.patients.models import AfyaIdentity, PatientFacility, Person
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


def _sensitive_disclosure_allowed(db: Session, patient_id: UUID) -> bool:
    try:
        from app.consent.models import SensitiveDiseaseConsent

        row = db.scalar(
            select(SensitiveDiseaseConsent.id).where(
                SensitiveDiseaseConsent.patient_id == patient_id,
                SensitiveDiseaseConsent.consent_given.is_(True),
            ).limit(1)
        )
        return row is not None
    except Exception:
        return False


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

    entries: list[dict] = []
    redacted = 0

    patient = _patient_resource(db, person)
    entries.append({"fullUrl": f"urn:uuid:{person.id}", "resource": patient})

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
                    "criticality": (a.severity or "unknown").lower(),
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
                    "medicationCodeableConcept": {"text": med.name if med else str(it.medication_id)},
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
                            "code": {
                                "text": test.name if test else "Lab result",
                                "coding": [{"code": test.code}] if test else [],
                            },
                            "subject": {"reference": f"Patient/{person.id}"},
                            "valueString": result.result,
                            "referenceRange": [{"text": result.reference_range}]
                            if result.reference_range
                            else [],
                            "issued": result.created_at.isoformat() if result.created_at else None,
                        },
                    }
                )

    if not _sensitive_disclosure_allowed(db, patient_id):
        redacted = 1

    bundle_id = str(uuid4())
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
        summary["entry"].insert(
            1,
            {
                "fullUrl": f"urn:uuid:{uuid4()}",
                "resource": {
                    "resourceType": "Composition",
                    "status": "final",
                    "type": {"text": "Referral note"},
                    "subject": {"reference": f"Patient/{patient_id}"},
                    "date": datetime.now(timezone.utc).isoformat(),
                    "title": "AfyaSync Referral Package",
                    "section": [
                        {
                            "title": "Clinical summary",
                            "text": {"div": clinical_summary[:4000]},
                        }
                    ],
                },
            },
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
    errors: list[str] = []
    if not isinstance(payload, dict):
        raise ValueError("INVALID_BUNDLE")
    if payload.get("resourceType") != "Bundle":
        errors.append("NOT_A_BUNDLE")
    btype = payload.get("type")
    if btype not in {"document", "collection", "transaction", "searchset"}:
        errors.append("UNSUPPORTED_BUNDLE_TYPE")
    entries = payload.get("entry") or []
    if not isinstance(entries, list) or len(entries) == 0:
        errors.append("EMPTY_BUNDLE")
    if len(entries) > 200:
        errors.append("BUNDLE_TOO_LARGE")

    patient_id = None
    has_patient = False
    for e in entries[:200]:
        if not isinstance(e, dict):
            errors.append("BAD_ENTRY")
            continue
        res = e.get("resource") or {}
        if res.get("resourceType") == "Patient":
            has_patient = True
            rid = res.get("id")
            if rid:
                try:
                    patient_id = UUID(str(rid))
                except Exception:
                    pass
    if not has_patient:
        errors.append("MISSING_PATIENT_RESOURCE")

    if source_node_id:
        node = db.get(HieNode, source_node_id)
        if node is None or node.status != "ACTIVE":
            errors.append("UNKNOWN_SOURCE_NODE")

    status = "REJECTED" if errors else "ACCEPTED"
    doc_type = "UNKNOWN"
    tags = (payload.get("meta") or {}).get("tag") or []
    for t in tags:
        if isinstance(t, dict) and t.get("code") in {"PATIENT_SUMMARY", "REFERRAL_PACKAGE"}:
            doc_type = t["code"]
            break

    row = HieInboundDocument(
        facility_id=facility_id,
        patient_id=patient_id,
        source_node_id=source_node_id,
        source_code=(source_code or "")[:80] or None,
        bundle_id=str(payload.get("id") or "")[:80] or None,
        document_type=doc_type,
        resource_count=len(entries) if isinstance(entries, list) else 0,
        validation_status=status,
        validation_errors=errors or None,
        payload_meta={
            "type": btype,
            "total": payload.get("total"),
            "timestamp": payload.get("timestamp"),
        },
        received_by=actor_user_id,
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


def upsert_node(db: Session, *, data: dict) -> HieNode:
    code = (data.get("code") or "").strip().upper()
    if not code:
        raise ValueError("NODE_CODE_REQUIRED")
    row = db.scalar(select(HieNode).where(HieNode.code == code))
    if row is None:
        row = HieNode(code=code)
        db.add(row)
    row.name = (data.get("name") or code)[:200]
    row.node_type = (data.get("node_type") or "FACILITY")[:40]
    row.endpoint_url = data.get("endpoint_url")
    row.facility_id = data.get("facility_id")
    row.trust_level = (data.get("trust_level") or "STANDARD")[:20]
    row.status = "ACTIVE"
    db.flush()
    return row


def list_nodes(db: Session, *, active_only: bool = True) -> list[HieNode]:
    q = select(HieNode).order_by(HieNode.name)
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
                    {"type": "Patient", "interaction": [{"code": "read"}]},
                    {"type": "AllergyIntolerance", "interaction": [{"code": "search-type"}]},
                    {"type": "Encounter", "interaction": [{"code": "search-type"}]},
                    {"type": "MedicationRequest", "interaction": [{"code": "search-type"}]},
                    {"type": "Observation", "interaction": [{"code": "search-type"}]},
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
