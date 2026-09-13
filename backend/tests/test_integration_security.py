from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.integrations.adapters import HttpJsonAdapter, build_adapter
from app.integrations.service import IntegrationError, _validate_configuration, update_integration_configuration


def test_integration_configuration_rejects_persisted_secret() -> None:
    with pytest.raises(IntegrationError, match="INTEGRATION_SECRET_MUST_USE_ENVIRONMENT"):
        _validate_configuration({"adapter_type": "http_json", "callback_secret": "plain-secret"})


def test_callback_secret_must_be_environment_backed() -> None:
    integration = SimpleNamespace(configuration={"callback_secret": "plain-secret"})
    with pytest.raises(IntegrationError, match="CALLBACK_SECRET_ENV_NOT_CONFIGURED"):
        from app.integrations.service import verify_callback_signature
        verify_callback_signature(integration, "0", "sha256=bad", {})


def test_http_adapter_requires_https() -> None:
    with pytest.raises(ValueError, match="HTTPS_ENDPOINT_REQUIRED"):
        HttpJsonAdapter(endpoint="http://payer.example.test/callback")


def test_http_adapter_is_buildable_from_non_secret_configuration() -> None:
    adapter = build_adapter({"adapter_type": "http_json", "endpoint": "https://payer.example.test/api", "credential_env": "AFYASYNC_PAYER_TOKEN"})
    assert isinstance(adapter, HttpJsonAdapter)


def test_configuration_changes_require_suspension() -> None:
    integration = SimpleNamespace(id="integration", facility_id="facility", status="ACTIVE", name="Payer", provider="PAYER", configuration={})
    db = MagicMock()
    db.scalar.return_value = integration

    with pytest.raises(IntegrationError, match="INTEGRATION_MUST_BE_SUSPENDED"):
        update_integration_configuration(
            db,
            integration.id,
            integration.facility_id,
            name="Updated",
            provider=None,
            configuration=None,
            reason="Operational change",
            actor_user_id="user",
        )
