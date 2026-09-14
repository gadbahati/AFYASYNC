from app.national_capacity.schemas import NationalCapacityResponse


def test_national_capacity_contract_contains_only_operational_fields():
    response = NationalCapacityResponse(
        active_facilities=1,
        active_departments=2,
        scheduled_appointments=3,
        waiting_queue_entries=4,
        total_beds=40,
        available_beds=12,
        occupied_beds=28,
        emergency_waiting=2,
        facilities=[{
            "facility_id": "facility",
            "facility_code": "KE-001",
            "facility_name": "Facility",
            "county": "Kirinyaga",
            "departments": 2,
            "scheduled_appointments": 3,
            "waiting_queue_entries": 4,
            "total_beds": 40,
            "available_beds": 12,
            "occupied_beds": 28,
            "emergency_waiting": 2,
        }],
    )
    dumped = response.model_dump()
    assert dumped["scheduled_appointments"] == 3
    assert dumped["waiting_queue_entries"] == 4
    assert dumped["total_beds"] == 40
    assert dumped["available_beds"] == 12
    assert dumped["occupied_beds"] == 28
    assert dumped["emergency_waiting"] == 2
    assert "patient_id" not in dumped
    assert "reason" not in dumped
    assert "clinical_summary" not in dumped
