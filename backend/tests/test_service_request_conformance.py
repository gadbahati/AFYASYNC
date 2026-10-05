from app.hie.conformance import validate_kenya_core_resource
from app.hie.service_request import KENYA_CORE_SERVICEREQUEST_PROFILE


def test_service_request_requires_coded_request():
    resource = {
        "resourceType": "ServiceRequest",
        "id": "order-1",
        "meta": {"profile": [KENYA_CORE_SERVICEREQUEST_PROFILE]},
        "status": "active",
        "intent": "order",
        "priority": "routine",
        "subject": {"reference": "Patient/patient-1"},
        "authoredOn": "2026-10-05T08:00:00+00:00",
        "requester": {"reference": "PractitionerRole/staff-1"},
    }
    errors = validate_kenya_core_resource(resource)
    assert "SERVICEREQUEST_CODE_CODING_REQUIRED" in errors


def test_service_request_with_coded_request_conforms():
    resource = {
        "resourceType": "ServiceRequest",
        "id": "order-1",
        "meta": {"profile": [KENYA_CORE_SERVICEREQUEST_PROFILE]},
        "status": "active",
        "intent": "order",
        "priority": "routine",
        "subject": {"reference": "Patient/patient-1"},
        "authoredOn": "2026-10-05T08:00:00+00:00",
        "requester": {"reference": "PractitionerRole/staff-1"},
        "code": {
            "coding": [{
                "system": "http://example.org/test",
                "code": "CBC",
                "display": "Complete blood count",
            }]
        },
    }
    assert validate_kenya_core_resource(resource) == []
