from datetime import datetime, timezone

from app.patients.timeline_router import _build_events


def test_build_events_merges_and_orders_longitudinal_care() -> None:
    record = {
        "encounters": [
            {
                "id": "enc-1",
                "encounter_id": "ENC-001",
                "started_at": datetime(2026, 1, 2, 10, tzinfo=timezone.utc),
                "status": "OPEN",
                "department_name": "Outpatient",
                "type": "OUTPATIENT",
                "reason": "Review",
                "consultation": None,
                "vitals": [],
                "diagnoses": [],
            }
        ],
        "care_plans": [
            {
                "id": "plan-1",
                "title": "Hypertension follow-up",
                "updated_at": datetime(2026, 1, 3, 10, tzinfo=timezone.utc),
                "created_at": datetime(2026, 1, 2, 10, tzinfo=timezone.utc),
                "status": "ACTIVE",
                "encounter_id": "enc-1",
                "goals": "Control blood pressure",
                "target_date": "2026-03-01",
            }
        ],
    }

    events = _build_events(record)

    assert [event.type for event in events] == ["CARE_PLAN", "ENCOUNTER"]
    assert events[0].title == "Hypertension follow-up"
    assert events[0].encounter_id == "enc-1"


def test_build_events_handles_optional_sections_without_failure() -> None:
    events = _build_events({"encounters": [], "care_plans": []})
    assert events == []
