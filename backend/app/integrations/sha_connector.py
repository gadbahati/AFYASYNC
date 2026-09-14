from __future__ import annotations

from urllib.parse import urlparse

from app.integrations.adapters import HttpJsonAdapter, IntegrationAdapter


class SHAConnectorError(ValueError):
    """Configuration or transport boundary error for the official SHA EDI connector."""


def build_sha_edi_adapter(configuration: dict) -> IntegrationAdapter:
    """Build a fail-closed connector for an authorised SHA EDI operation endpoint.

    AfyaSync deliberately does not guess SHA operation paths or response fields. The
    exact operation endpoint supplied by SHA is configured per facility integration.
    Production only accepts SHA-owned hosts so an accidental third-party endpoint
    cannot be registered as the SHA connector.
    """
    if not isinstance(configuration, dict):
        raise SHAConnectorError("INVALID_SHA_CONNECTOR_CONFIGURATION")

    endpoint = configuration.get("endpoint")
    credential_env = configuration.get("credential_env")
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise SHAConnectorError("SHA_ENDPOINT_REQUIRED")
    if not isinstance(credential_env, str) or not credential_env.strip():
        raise SHAConnectorError("SHA_CREDENTIAL_ENV_REQUIRED")

    parsed = urlparse(endpoint.strip())
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() != "https" or not hostname.endswith(".sha.go.ke"):
        raise SHAConnectorError("SHA_ENDPOINT_MUST_BE_HTTPS_SHA_HOST")

    timeout = configuration.get("timeout_seconds", 20)
    if not isinstance(timeout, int):
        raise SHAConnectorError("INVALID_SHA_CONNECTOR_TIMEOUT")

    return HttpJsonAdapter(
        endpoint=endpoint.strip(),
        credential_env=credential_env.strip(),
        timeout_seconds=timeout,
    )
