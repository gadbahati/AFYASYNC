# Phase 5 — Production readiness controls

## Activation gate
Facilities cannot transition to ACTIVE through the managed status workflow unless identity, county/sub-county, an official registration or licence identifier, and at least one active department are present. Readiness is exposed as an aggregate national operations check; patient data is not included.

## Transaction safety
Integration transactions use bounded listings, row locking during state updates, and explicit legal state transitions. A successful transaction is terminal except for an idempotent repeat of SUCCESS; conflicting external references are rejected.

## Interoperability contract
The API declares FHIR R4 resources/profiles and the AfyaSync identifier system, plus the supported DHIS2 API version. Contract regression coverage protects these declarations.

## Operational verification
Railway deployment health must be checked after each production change. The application readiness endpoint performs a database connectivity check and returns HTTP 503 when the database is unavailable. The service must not be treated as production-ready solely from deployment status; backup/restore drills, incident response, security review, legal/privacy review, interoperability partner certification, and pilot acceptance remain operational gates.

## Backup and recovery gate
Database backups and restore drills are infrastructure responsibilities and must be evidenced outside application code. A production launch should record backup frequency, retention, encryption, restore test date, recovery point objective, recovery time objective, and the owner responsible for each control.
