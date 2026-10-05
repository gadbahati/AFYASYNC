from pathlib import Path

SERVICE = Path(__file__).parents[1] / "app" / "hie" / "delivery_service.py"


def test_phase207_rechecks_enrollment_before_send():
    source = SERVICE.read_text()
    assert 'PATIENT_NOT_ENROLLED_AT_FACILITY' in source
    assert 'HieDeliveryJob' in source
    assert 'PatientFacility.status == "ACTIVE"' in source


def test_phase207_rechecks_destination_trust_before_send():
    source = SERVICE.read_text()
    assert 'HIE_DESTINATION_SELF' in source
    assert 'HIE_DESTINATION_NOT_TRUSTED' in source
    assert 'node.trust_level not in {"HIGH", "NATIONAL"}' in source


def test_phase207_does_not_send_retry_jobs_before_due_time():
    source = SERVICE.read_text()
    assert 'HIE_DELIVERY_RETRY_NOT_DUE' in source
    assert 'job.status == "RETRY"' in source
    assert 'job.next_attempt_at > now' in source


def test_phase207_rejects_invalid_success_responses():
    source = SERVICE.read_text()
    assert 'HIE_INVALID_SUCCESS_RESPONSE' in source
    assert 'HIE_INVALID_SUCCESS_CONTENT_TYPE' in source
    assert 'HIE_UNEXPECTED_SUCCESS_RESOURCE' in source
    assert 'response_json.get("resourceType") not in {"Bundle", "OperationOutcome"}' in source
