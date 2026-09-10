# AfyaSync

**Healthcare, connected.**

AfyaSync is a standalone healthcare platform designed to connect patients, healthcare facilities, clinical workflows, billing, payments, claims, and authorised healthcare integrations through one secure platform.

> AfyaSync is the platform. SHA is an integrated capability.

## Project status

Early MVP development.

## Architecture

- Backend: Python + FastAPI
- Database: PostgreSQL
- Web: React + TypeScript
- Mobile: Flutter
- Background jobs: Redis + worker
- Authentication: JWT, refresh tokens, OTP/MFA
- Deployment: Docker

## Repository structure

```text
afasync/
├── backend/
├── frontend/
├── mobile/
├── ussd/
├── database/
├── docs/
├── infrastructure/
└── tests/
```

## Development principles

- One person = one AfyaSync ID.
- Coverage is separate from identity.
- Every clinical and financial event belongs to an encounter where applicable.
- Facility access is isolated and permission-controlled.
- Important actions are audited.
- Medical and financial history is preserved rather than silently deleted.
- External integrations must be authorised and resilient to temporary failures.
- No production secrets are committed to Git.

## MVP flow

`LOGIN → FACILITY → PATIENT REGISTRATION → PATIENT SEARCH → ENCOUNTER → QUEUE → CLINICAL → LAB → PHARMACY → BILLING → PAYMENT → REPORTS`

## Security

AfyaSync is intended for regulated healthcare use. Production deployment requires appropriate legal, regulatory, privacy, security, licensing, accreditation, payer, and integration review before real patient data is used.
