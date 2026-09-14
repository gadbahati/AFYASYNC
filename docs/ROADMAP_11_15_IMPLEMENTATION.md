# Roadmap 11–15 implementation status

## 11 Offline resilience
The backend keeps external integration work asynchronous and retryable. No disconnected mode is enabled that could invent payer or clinical outcomes. A durable offline client remains a controlled future capability requiring local persistence, sync conflict rules and security testing.

## 12 Patient/member access
Existing patient/portal capabilities remain authenticated and scoped. Coverage verification remains distinct from AfyaSync identity. Personal data is not added to national operational telemetry.

## 13 Clinical departments
Existing department modules are registered through the common application spine and retain facility/RBAC controls. No duplicate patient identity layer is introduced.

## 14 Notifications
Notification workflows remain minimal-data and event driven. Referral/transfer status notifications must not carry clinical notes, diagnoses or unnecessary identifiers.

## 15 Observability
A protected runtime snapshot is available at `/api/v1/observability/runtime` under `operations.observability.read`. It contains only process start time and aggregate request/error counters. It deliberately excludes request payloads and patient identifiers.

This document records engineering state; it is not a claim that external clinical, regulatory, telecom or government approvals have been obtained.
