"""Phase 174: Kenya Core profile-aware FHIR conformance checks.

These checks intentionally validate structural requirements that are safely
enforceable locally. They do not claim full IG validator parity.
"""
from __future__ import annotations

from typing import Any

KENYA_CORE_BASE = "https://fhir.dha.go.ke/core/StructureDefinition/"
KPS_BASE = "https://fhir.dha.go.ke/kps/StructureDefinition/"
KPS_IMAGING_STUDY_PROFILE = KPS_BASE + "ke-kps-imaging-study"
KPS_DIAGNOSTIC_REPORT_PROFILE = KPS_BASE + "ke-kps-diagnostic-report"
KENYA_CORE_PROFILES = {
    "Patient": KENYA_CORE_BASE + "kenya-core-patient|1.0.0",
    "Encounter": KENYA_CORE_BASE + "kenya-core-encounter|1.0.0",
    "Observation": KENYA_CORE_BASE + "kenya-core-observation|1.0.0",
    "Condition": KENYA_CORE_BASE + "condition|1.0.0",
    "Procedure": KENYA_CORE_BASE + "kenya-core-procedure|1.0.0",
    "ImagingStudy": KPS_IMAGING_STUDY_PROFILE,
    "DiagnosticReportKPS": KPS_DIAGNOSTIC_REPORT_PROFILE,
    "Organization": KENYA_CORE_BASE + "provider-organization|1.0.0",
    "Provenance": KENYA_CORE_BASE + "kenya-core-provenance|1.0.0",
    "Practitioner": KENYA_CORE_BASE + "practitioner-sha-ke|1.0.0",
    "PractitionerRole": KENYA_CORE_BASE + "kenya-core-practitionerrole|1.0.0",
    "Location": KENYA_CORE_BASE + "kenya-core-location|1.0.0",
    "ServiceRequest": KENYA_CORE_BASE + "kenya-core-servicerequest|1.0.0",
    "Task": KENYA_CORE_BASE + "kenya-core-task|1.0.0",
    "Communication": KENYA_CORE_BASE + "kenya-core-communication|1.0.0",
    "ServiceRequest": KENYA_CORE_BASE + "kenya-core-servicerequest|1.0.0",
    "DiagnosticReport": KENYA_CORE_BASE + "kenya-core-diagnosticreport|1.0.0",
    "Procedure": KENYA_CORE_BASE + "kenya-core-procedure|1.0.0",
}

def _profile(resource: dict) -> str | None:
    profiles = (resource.get("meta") or {}).get("profile") or []
    return profiles[0] if profiles else None

def validate_kenya_core_resource(resource: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(resource, dict):
        return ["RESOURCE_NOT_OBJECT"]
    rt = resource.get("resourceType")
    if rt not in KENYA_CORE_PROFILES:
        return []
    if not resource.get("id"):
        errors.append(f"{rt}_MISSING_ID")
    profile = _profile(resource)
    expected_profile = KENYA_CORE_PROFILES[rt]
    if rt == "DiagnosticReport" and profile not in {expected_profile, KPS_DIAGNOSTIC_REPORT_PROFILE}:
        errors.append(f"{rt}_MISSING_KENYA_CORE_PROFILE")
    elif rt != "DiagnosticReport" and profile != expected_profile:
        errors.append(f"{rt}_MISSING_KENYA_CORE_PROFILE")
    if rt == "Patient" and not resource.get("name"):
        errors.append("PATIENT_NAME_REQUIRED")
    if rt == "Encounter":
        if not resource.get("subject"):
            errors.append("ENCOUNTER_SUBJECT_REQUIRED")
        if not resource.get("class"):
            errors.append("ENCOUNTER_CLASS_REQUIRED")
    if rt == "Observation":
        for field in ("status", "category", "code", "subject", "effectiveDateTime"):
            if not resource.get(field):
                errors.append(f"OBSERVATION_{field.upper()}_REQUIRED")
    if rt == "Condition":
        if not resource.get("subject"):
            errors.append("CONDITION_SUBJECT_REQUIRED")
        if not resource.get("code"):
            errors.append("CONDITION_CODE_REQUIRED")
    if rt == "Organization" and not resource.get("identifier"):
        errors.append("ORGANIZATION_IDENTIFIER_REQUIRED")
    if rt == "ServiceRequest":
        if not resource.get("subject"):
            errors.append("SERVICEREQUEST_SUBJECT_REQUIRED")
        if not resource.get("authoredOn"):
            errors.append("SERVICEREQUEST_AUTHORED_ON_REQUIRED")
        if not resource.get("code") or not resource["code"].get("coding"):
            errors.append("SERVICEREQUEST_CODE_CODING_REQUIRED")
        if not resource.get("requester"):
            errors.append("SERVICEREQUEST_REQUESTER_REQUIRED")
    if rt == "ImagingStudy":
        for field in ("status", "subject", "started", "modality"):
            if not resource.get(field):
                errors.append("IMAGINGSTUDY_" + field.upper() + "_REQUIRED")
    if rt == "ImagingStudy":
        for field in ("status", "subject", "started", "modality"):
            if not resource.get(field):
                errors.append("IMAGINGSTUDY_" + field.upper() + "_REQUIRED")
    if rt == "Procedure":
        for field in ("status", "code", "subject", "performedDateTime", "performer"):
            if not resource.get(field):
                errors.append("PROCEDURE_" + field.upper() + "_REQUIRED")
    if rt == "DiagnosticReport":
        for field in ("status", "code", "subject", "encounter", "effectiveDateTime", "issued", "performer"):
            if not resource.get(field):
                errors.append("DIAGNOSTICREPORT_" + field.upper() + "_REQUIRED")
        if profile == KPS_DIAGNOSTIC_REPORT_PROFILE:
            if not resource.get("imagingStudy") and not resource.get("result"):
                errors.append("DIAGNOSTICREPORT_IMAGING_OR_RESULT_REQUIRED")
        else:
            for field in ("category", "result"):
                if not resource.get(field):
                    errors.append("DIAGNOSTICREPORT_" + field.upper() + "_REQUIRED")
    if rt == "Communication":
        for field in ("identifier", "subject", "recipient", "sender", "payload"):
            if not resource.get(field):
                errors.append("COMMUNICATION_" + field.upper() + "_REQUIRED")
    if rt == "Task":
        for field in ("status", "intent", "priority", "code", "description", "focus", "for", "authoredOn"):
            if not resource.get(field):
                errors.append("TASK_" + field.upper().replace("-", "_") + "_REQUIRED")
    if rt == "Practitioner" and not resource.get("name"):
        errors.append("PRACTITIONER_NAME_REQUIRED")
    if rt == "PractitionerRole":
        if not resource.get("practitioner"):
            errors.append("PRACTITIONER_ROLE_PRACTITIONER_REQUIRED")
        if not resource.get("organization"):
            errors.append("PRACTITIONER_ROLE_ORGANIZATION_REQUIRED")
        if not resource.get("code"):
            errors.append("PRACTITIONER_ROLE_CODE_REQUIRED")
    if rt == "Location":
        if not resource.get("name"):
            errors.append("LOCATION_NAME_REQUIRED")
        if not resource.get("managingOrganization"):
            errors.append("LOCATION_MANAGING_ORGANIZATION_REQUIRED")
    if rt == "Provenance":
        for field in ("target", "recorded", "agent"):
            if not resource.get(field):
                errors.append(f"PROVENANCE_{field.upper()}_REQUIRED")
    return errors

def validate_bundle(bundle: Any, *, require_patient: bool = True, require_provenance: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(bundle, dict):
        return ["INVALID_BUNDLE"]
    if bundle.get("resourceType") != "Bundle":
        errors.append("NOT_A_BUNDLE")
    if bundle.get("type") not in {"document", "collection", "transaction", "searchset"}:
        errors.append("UNSUPPORTED_BUNDLE_TYPE")
    if not bundle.get("id"):
        errors.append("MISSING_BUNDLE_ID")
    entries = bundle.get("entry")
    if not isinstance(entries, list) or not entries:
        errors.append("EMPTY_BUNDLE")
        return errors
    if len(entries) > 200:
        errors.append("BUNDLE_TOO_LARGE")
    patient_count = provenance_count = 0
    for index, entry in enumerate(entries[:200]):
        if not isinstance(entry, dict):
            errors.append(f"BAD_ENTRY_{index}")
            continue
        resource = entry.get("resource")
        if not isinstance(resource, dict):
            errors.append(f"MISSING_RESOURCE_{index}")
            continue
        if not resource.get("resourceType"):
            errors.append(f"MISSING_RESOURCE_TYPE_{index}")
        if not resource.get("id"):
            errors.append(f"MISSING_RESOURCE_ID_{index}")
        if not entry.get("fullUrl"):
            errors.append(f"MISSING_FULL_URL_{index}")
        errors.extend(f"ENTRY_{index}_{e}" for e in validate_kenya_core_resource(resource))
        if resource.get("resourceType") == "Patient":
            patient_count += 1
        if resource.get("resourceType") == "Provenance":
            provenance_count += 1
    if require_patient and patient_count != 1:
        errors.append("PATIENT_RESOURCE_COUNT_INVALID")
    if require_provenance and provenance_count != 1:
        errors.append("PROVENANCE_RESOURCE_COUNT_INVALID")
    if bundle.get("type") == "document":
        first = entries[0].get("resource") if isinstance(entries[0], dict) else None
        if not isinstance(first, dict) or first.get("resourceType") != "Composition":
            errors.append("DOCUMENT_COMPOSITION_MUST_BE_FIRST")
    return errors

def assert_valid_bundle(bundle: dict) -> None:
    errors = validate_bundle(bundle, require_provenance=True)
    if errors:
        raise ValueError("HIE_FHIR_CONFORMANCE_FAILED:" + ",".join(errors))
