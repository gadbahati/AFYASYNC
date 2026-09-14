# AfyaSync Roadmap Items 11–22

This roadmap extends the production foundation beyond the initial national operations and security work. Each item is an engineering gate, not a claim of regulatory approval, government adoption, or production authorization.

## 11 — Offline facility resilience
Core workflows must fail safely when an external payer or interoperability service is unavailable. Clinical and cash workflows remain independent of payer connectivity; queued integration work is retryable and auditable.

## 12 — Member / patient access
Patient-facing capabilities must expose only the minimum information required for self-service, require authenticated sessions where personal data is involved, and never treat a payer lookup as a replacement for AfyaSync identity.

## 13 — Clinical department depth
The platform keeps specialty workflows separated by domain while preserving a shared patient/encounter/clinical-event spine. Department modules must enforce facility isolation and permissions.

## 14 — Notifications and operational events
Notifications are event-driven, minimal and non-sensitive. Referral and transfer status changes may notify the patient without embedding diagnoses, clinical notes or other sensitive payloads.

## 15 — Production observability
Production operations require health/readiness checks, request IDs, auditability, integration transaction monitoring, structured error handling, backups and tested recovery. Runtime metrics must remain aggregate and privacy-safe.

## 16 — Privacy and data governance
Every patient-data surface must have an explicit purpose, least-privilege access, audit coverage, retention/deletion rules where legally permitted, and privacy-safe logs. Sensitive identifiers must not leak through operational telemetry, error messages, URLs, exports, or analytics.

## 17 — Interoperability conformance
FHIR, DHIS2 and payer adapters must use explicit version/profile mappings, external identifier mappings, validation, contract tests, retry/idempotency semantics and environment-specific configuration. No placeholder identifier may be presented as an official national identifier.

## 18 — Transactional workflow integrity
High-value clinical and financial workflows must be idempotent where retries are possible, preserve state transitions, reject invalid transitions, and make external side effects auditable. Claims, payments, referrals, transfers and callbacks must not silently duplicate.

## 19 — Scale and performance
National workloads must use bounded pagination, indexed queries, connection-pool discipline, background processing for long operations, cacheable aggregate views where appropriate, and load/performance tests before scale-up. Patient-level data must not be used as an unrestricted national analytics payload.

## 20 — Facility onboarding and configuration
Facility onboarding must be repeatable and configuration-driven: facility identity, departments, staff, roles, services, payer participation, identifiers, operating status and integration mappings must be validated before activation. Bootstrap credentials and pilot data must never be required for production.

## 21 — National intelligence and financial control
National reporting must distinguish operational, clinical, utilisation and financial aggregates; expose provenance and time windows; support reconciliation; and avoid patient-level disclosure. Financial intelligence must reconcile claims, payments and payer responses rather than relying on UI-only totals.

## 22 — Production-scale readiness
The final gate combines security, reliability, interoperability, clinical workflow, financing, facility onboarding, observability, backup/restore, incident response, performance, user acceptance and pilot evidence. Go-live remains subject to the applicable Kenyan legal, regulatory, clinical, privacy, payer and government approvals.

### Current engineering status
- Items 11–15: foundation implemented and hardened; observability runtime counters are now wired into API request handling and covered by regression tests.
- Items 16–22: the engineering track continues from the controls above. These are not considered complete merely because a route, document or UI exists; each requires implementation, tests and operational evidence before being marked complete.
