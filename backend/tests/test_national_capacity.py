from app.national_capacity.schemas import NationalCapacityResponse


def test_national_capacity_contract_contains_only_operational_fields():
    response = NationalCapacityResponse(
        active_facilities=1, active_departments=2, scheduled_appointments=3, waiting_queue_entries=4,
        total_beds=10, available_beds=6, occupied_beds=4, emergency_waiting=1,
        facilities=[{"facility_id": "facility", "facility_code": "KE-001", "facility_name": "Facility", "county": "Kirinyaga", "departments": 2, "scheduled_appointments": 3, "waiting_queue_entries": 4, "total_beds": 10, "available_beds": 6, "occupied_beds": 4, "emergency_waiting": 1}],
    )
    dumped = response.model_dump()
    assert dumped["scheduled_appointments"] == 3
    assert dumped["waiting_queue_entries"] == 4
    assert dumped["available_beds"] == 6
    assert "patient_id" not in dumped
    assert "reason" not in dumped
    assert "clinical_summary" not in dumped
