# AfyaSync Roadmap Items 11–15

Items 11–15 complete the platform foundation around patient engagement, notifications, supply operations, administration and production observability.

## 11 — Offline facility resilience
Core workflows must fail safely when an external payer or interoperability service is unavailable. Clinical and cash workflows remain independent of payer connectivity; queued integration work is retryable and auditable.

## 12 — Member / patient access
Patient-facing capabilities must expose only the minimum information required for self-service, require authenticated sessions where personal data is involved, and never treat a payer lookup as a replacement for AfyaSync identity.

## 13 — Clinical department depth
The platform keeps specialty workflows separated by domain while preserving a shared patient/encounter/clinical-event spine. Department modules must enforce facility isolation and permissions.

## 14 — Notifications and operational events
Notifications are event-driven, minimal and non-sensitive. Referral and transfer status changes may notify the patient without embedding diagnoses, clinical notes or other sensitive payloads.

## 15 — Production observability
Production operations require health/readiness checks, request IDs, auditability, integration transaction monitoring, structured error handling, backups and tested recovery. Metrics should support operators without exposing patient-level data.
