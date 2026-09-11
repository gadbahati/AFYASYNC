from uuid import uuid4
from unittest.mock import Mock

import app.patients.service as patient_service
from app.patients.service import search_patients


def test_search_patients_scopes_query_to_facility(monkeypatch) -> None:
    db = Mock()
    execute_result = Mock()
    execute_result.all.return_value = []
    db.execute.return_value = execute_result

    captured = {}

    class Statement:
        def where(self, *criteria):
            captured["criteria"] = criteria
            return self

        def order_by(self, *criteria):
            return self

        def limit(self, value):
            captured["limit"] = value
            return self

    statement = Statement()
    monkeypatch.setattr(patient_service, "select", lambda *args: statement)

    facility_id = uuid4()
    result = search_patients(db, "Jane", facility_id, 10)

    assert result == []
    assert captured["limit"] == 10
    assert len(captured["criteria"]) == 3
    assert any("patient_facilities.facility_id" in str(criteria) for criteria in captured["criteria"])
    assert any("patient_facilities.status" in str(criteria) for criteria in captured["criteria"])
