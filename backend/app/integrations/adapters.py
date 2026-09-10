from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AdapterResult:
    status: str
    response_code: str | None = None
    external_reference: str | None = None
    response_data: dict | None = None


class IntegrationAdapter(Protocol):
    """Adapter contract for authorised external systems.

    Implementations must use credentials and endpoints supplied by the deployment
    configuration. AfyaSync never fabricates external approvals or payment results.
    """

    def send(self, payload: dict, idempotency_key: str) -> AdapterResult:
        ...


class UnconfiguredAdapter:
    """Safe default: retain the transaction locally until an authorised adapter exists."""

    def send(self, payload: dict, idempotency_key: str) -> AdapterResult:
        return AdapterResult(status="RETRYING", response_code="ADAPTER_NOT_CONFIGURED", response_data={"message": "Authorised integration adapter is not configured"})
