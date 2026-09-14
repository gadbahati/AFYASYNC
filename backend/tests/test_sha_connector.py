import pytest

from app.integrations.adapters import HttpJsonAdapter, build_adapter
from app.integrations.sha_connector import SHAConnectorError, build_sha_edi_adapter


def test_sha_edi_requires_sha_host_and_credentials() -> None:
    adapter = build_sha_edi_adapter({
        "adapter_type": "sha_edi",
        "endpoint": "https://edi-api.provider-uat.sha.go.ke/eligibility",
        "credential_env": "SHA_UAT_TOKEN",
    })
    assert isinstance(adapter, HttpJsonAdapter)


def test_sha_edi_rejects_non_sha_endpoint() -> None:
    with pytest.raises(SHAConnectorError, match="SHA_ENDPOINT_MUST_BE_HTTPS_SHA_HOST"):
        build_sha_edi_adapter({
            "adapter_type": "sha_edi",
            "endpoint": "https://example.com/eligibility",
            "credential_env": "SHA_UAT_TOKEN",
        })


def test_sha_edi_requires_credential_environment() -> None:
    with pytest.raises(SHAConnectorError, match="SHA_CREDENTIAL_ENV_REQUIRED"):
        build_sha_edi_adapter({
            "adapter_type": "sha_edi",
            "endpoint": "https://edi-api.provider-uat.sha.go.ke/eligibility",
        })


def test_build_adapter_supports_sha_edi() -> None:
    adapter = build_adapter({
        "adapter_type": "sha_edi",
        "endpoint": "https://api-edi.provider.sha.go.ke/eligibility",
        "credential_env": "SHA_PRODUCTION_TOKEN",
    })
    assert isinstance(adapter, HttpJsonAdapter)
