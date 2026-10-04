"""Phase 170: lightweight FHIR bundle conformance checks before exchange."""
from __future__ import annotations
from typing import Any

ALLOWED_BUNDLE_TYPES = {"document", "collection", "transaction", "searchset"}

def validate_bundle(bundle: Any, *, require_patient: bool = True) -> list[str]:
    errors: list[str] = []
    if not isinstance(bundle, dict):
        return ["INVALID_BUNDLE"]
    if bundle.get("resourceType") != "Bundle":
        errors.append("NOT_A_BUNDLE")
    if bundle.get("type") not in ALLOWED_BUNDLE_TYPES:
        errors.append("UNSUPPORTED_BUNDLE_TYPE")
    if not bundle.get("id"):
        errors.append("MISSING_BUNDLE_ID")
    entries = bundle.get("entry")
    if not isinstance(entries, list) or not entries:
        errors.append("EMPTY_BUNDLE")
        return errors
    if len(entries) > 200:
        errors.append("BUNDLE_TOO_LARGE")
    patient_count = 0
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
        if resource.get("resourceType") == "Patient":
            patient_count += 1
    if require_patient and patient_count != 1:
        errors.append("PATIENT_RESOURCE_COUNT_INVALID")
    if bundle.get("type") == "document":
        first = entries[0].get("resource") if isinstance(entries[0], dict) else None
        if not isinstance(first, dict) or first.get("resourceType") != "Composition":
            errors.append("DOCUMENT_COMPOSITION_MUST_BE_FIRST")
    return errors

def assert_valid_bundle(bundle: dict) -> None:
    errors = validate_bundle(bundle)
    if errors:
        raise ValueError("HIE_FHIR_CONFORMANCE_FAILED:" + ",".join(errors))
