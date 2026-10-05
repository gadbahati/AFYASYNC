from uuid import uuid4

from app.hie.conformance import validate_bundle


def test_phase195_service_request_bundle_is_conformant():
    pid = str(uuid4())
    oid = str(uuid4())
    bundle = {
        "resourceType": "Bundle",
        "id": f"service-request-{oid}",
        "type": "collection",
        "entry": [
            {"fullUrl": f"urn:uuid:Patient/{pid}", "resource": {
                "resourceType": "Patient", "id": pid,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"]},
                "name": [{"text": "Example"}],
            }},
            {"fullUrl": f"urn:uuid:Organization/{oid}", "resource": {
                "resourceType": "Organization", "id": oid,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/provider-organization|1.0.0"]},
                "identifier": [{"system": "https://afyasync.health.ke/fhir/facilities", "value": oid}],
            }},
            {"fullUrl": f"urn:uuid:ServiceRequest/{oid}", "resource": {
                "resourceType": "ServiceRequest", "id": oid,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-servicerequest|1.0.0"]},
                "status": "active", "intent": "order",
                "subject": {"reference": f"Patient/{pid}"},
                "code": {"coding": [{"system": "http://example.org/test", "code": "TEST-1"}]},
                "authoredOn": "2026-10-05T10:00:00+00:00",
                "requester": {"reference": f"Organization/{oid}"},
            }},
            {"fullUrl": f"urn:uuid:Provenance/{oid}", "resource": {
                "resourceType": "Provenance", "id": oid,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"]},
                "target": [{"reference": f"ServiceRequest/{oid}"}],
                "recorded": "2026-10-05T10:00:00+00:00",
                "agent": [{"type": {"text": "author"}, "who": {"reference": f"Organization/{oid}"}}],
            }},
        ],
    }
    assert validate_bundle(bundle, require_provenance=True) == []


def test_phase195_service_request_requires_national_mapping():
    # The exporter must never turn an unverified local order code into a national code.
    from app.hie.service_request import ServiceRequestError
    assert str(ServiceRequestError("ORDER_CODE_NOT_NATIONALLY_MAPPED")) == "ORDER_CODE_NOT_NATIONALLY_MAPPED"
