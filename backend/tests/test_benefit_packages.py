from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import MagicMock, patch

from app.benefits.service import list_active_benefit_packages


def test_list_active_benefit_packages_returns_catalog_and_audits() -> None:
    packages = [
        SimpleNamespace(package_code="SHA-07", name="Hospital Admissions / Inpatient Services"),
        SimpleNamespace(package_code="SHA-08", name="Maternal and Child Health Services"),
    ]
    db = MagicMock()
    db.scalars.return_value.all.return_value = packages

    facility_id = uuid4()
    actor_user_id = uuid4()

    with patch("app.benefits.service.record_audit") as record_audit:
        result = list_active_benefit_packages(
            db,
            facility_id=facility_id,
            actor_user_id=actor_user_id,
        )

    assert result == packages
    record_audit.assert_called_once()
    audit_kwargs = record_audit.call_args.kwargs
    assert audit_kwargs["action"] == "VIEW_BENEFIT_PACKAGES"
    assert audit_kwargs["facility_id"] == facility_id
    assert audit_kwargs["user_id"] == actor_user_id
    assert audit_kwargs["metadata"] == {"package_count": 2}
    assert audit_kwargs["commit"] is False
    db.commit.assert_called_once()
