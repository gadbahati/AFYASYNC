from app.hie.conformance import validate_kenya_core_resource
from app.hie.referral_task import _PRIORITY, _STATUS


def test_referral_status_maps_to_fhir_task_status():
    assert _STATUS["SENT"] == "requested"
    assert _STATUS["ACCEPTED"] == "accepted"
    assert _STATUS["IN_PROGRESS"] == "in-progress"
    assert _STATUS["COMPLETED"] == "completed"
    assert _STATUS["DECLINED"] == "failed"
    assert _STATUS["CANCELLED"] == "cancelled"


def test_referral_priority_maps_to_fhir_priority():
    assert _PRIORITY == {
        "ROUTINE": "routine",
        "URGENT": "urgent",
        "EMERGENCY": "stat",
    }


def test_kenya_core_task_conformance_requires_workflow_fields():
    task = {
        "resourceType": "Task",
        "id": "task-1",
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-task|1.0.0"
            ]
        },
        "status": "requested",
        "intent": "order",
        "priority": "routine",
        "code": {"text": "Referral coordination"},
        "description": "Specialist review",
        "focus": {"reference": "ServiceRequest/sr-1"},
        "for": {"reference": "Patient/p-1"},
        "authoredOn": "2026-10-05T10:00:00+00:00",
    }
    assert validate_kenya_core_resource(task) == []


def test_kenya_core_task_rejects_missing_focus():
    task = {
        "resourceType": "Task",
        "id": "task-1",
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-task|1.0.0"
            ]
        },
        "status": "requested",
        "intent": "order",
        "priority": "routine",
        "code": {"text": "Referral coordination"},
        "description": "Specialist review",
        "for": {"reference": "Patient/p-1"},
        "authoredOn": "2026-10-05T10:00:00+00:00",
    }
    assert "TASK_FOCUS_REQUIRED" in validate_kenya_core_resource(task)
