from dataclasses import dataclass
import json
import os
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class AdapterResult:
    status: str
    response_code: str | None = None
    external_reference: str | None = None
    response_data: dict | None = None


class IntegrationAdapter(Protocol):
    """Adapter contract for authorised external systems."""

    def send(self, payload: dict, idempotency_key: str) -> AdapterResult:
        ...


class UnconfiguredAdapter:
    """Safe default: retain the transaction locally until an authorised adapter exists."""

    def send(self, payload: dict, idempotency_key: str) -> AdapterResult:
        return AdapterResult(
            status="RETRYING",
            response_code="ADAPTER_NOT_CONFIGURED",
            response_data={"message": "Authorised integration adapter is not configured"},
        )


class HttpJsonAdapter:
    """Minimal HTTPS JSON adapter for an authorised external endpoint.

    Secrets are read from an environment variable named by configuration rather
    than persisted in the integration record. Only HTTPS endpoints are allowed.
    The adapter reports transport/application responses; it never invents payer
    approval, rejection, or payment state.
    """

    def __init__(self, *, endpoint: str, credential_env: str | None = None, timeout_seconds: int = 20):
        if not endpoint.startswith("https://"):
            raise ValueError("HTTPS_ENDPOINT_REQUIRED")
        self.endpoint = endpoint
        self.credential_env = credential_env
        self.timeout_seconds = max(1, min(timeout_seconds, 60))

    def send(self, payload: dict, idempotency_key: str) -> AdapterResult:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        if self.credential_env:
            credential = os.getenv(self.credential_env)
            if not credential:
                return AdapterResult(
                    status="RETRYING",
                    response_code="ADAPTER_CREDENTIAL_NOT_CONFIGURED",
                    response_data={},
                )
            headers["Authorization"] = f"Bearer {credential}"

        request = Request(
            self.endpoint,
            data=json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
                if not isinstance(data, dict):
                    data = {"body": data}
                return AdapterResult(
                    status="SUCCEEDED",
                    response_code=str(response.status),
                    external_reference=data.get("external_reference"),
                    response_data=data,
                )
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                data = {"body": raw[:2000]}
            return AdapterResult(
                status="RETRYING" if exc.code >= 500 else "FAILED",
                response_code=str(exc.code),
                response_data=data if isinstance(data, dict) else {"body": data},
            )
        except (URLError, TimeoutError, OSError):
            return AdapterResult(status="RETRYING", response_code="TRANSPORT_ERROR", response_data={})


def build_adapter(configuration: dict | None) -> IntegrationAdapter:
    """Build only explicitly configured adapters; never silently fake success."""
    configuration = configuration or {}
    adapter_type = configuration.get("adapter_type", "unconfigured")
    if adapter_type == "http_json":
        endpoint = configuration.get("endpoint")
        if not isinstance(endpoint, str) or not endpoint:
            raise ValueError("ADAPTER_ENDPOINT_REQUIRED")
        credential_env = configuration.get("credential_env")
        if credential_env is not None and not isinstance(credential_env, str):
            raise ValueError("INVALID_CREDENTIAL_ENV")
        timeout = configuration.get("timeout_seconds", 20)
        if not isinstance(timeout, int):
            raise ValueError("INVALID_ADAPTER_TIMEOUT")
        return HttpJsonAdapter(endpoint=endpoint, credential_env=credential_env, timeout_seconds=timeout)
    if adapter_type == "unconfigured":
        return UnconfiguredAdapter()
    raise ValueError("UNSUPPORTED_ADAPTER_TYPE")
