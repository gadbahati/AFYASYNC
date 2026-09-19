# AfyaSync

**Healthcare, connected.**

AfyaSync is a standalone healthcare platform designed to connect patients, healthcare facilities, clinical workflows, billing, payments, claims, reporting, and authorised healthcare integrations through one secure platform.

> AfyaSync is the platform. SHA is an integrated capability.

**Developed by Bahati GAD**

© 2026 AfyaSync. Developed by Bahati GAD. All rights reserved.  
Unauthorized copying, reverse engineering, redistribution, or commercial use of this software, its design, architecture, source code, or documentation is strictly prohibited and will be prosecuted under Kenyan and international law.

## Project status

Active platform development with production-readiness controls and a national healthcare operating architecture. The repository is not a claim of regulatory approval or government adoption.

## Architecture

- Backend: Python + FastAPI
- Database: PostgreSQL
- Web: React + TypeScript
- Background jobs: dedicated integration worker
- Authentication: JWT access/refresh sessions with rotation and revocation
- Deployment: Docker / Railway / Render configuration included
- Schema management: Alembic migrations

## Core platform capabilities

- Patient identity, registration, encounters, queues, referrals, and clinical workflows
- Laboratory, pharmacy, radiology, theatre, maternity, nursing, wards, and other clinical services
- Billing, payments, payer coverage, benefits, preauthorisation, claims, rework, and reconciliation
- Facility, staff, payer, and benefit network administration with explicit national permissions
- National reporting and operational command-centre intelligence
- Authorised payer integrations with signed callbacks, idempotency, retry handling, and transaction monitoring
- Audit trails and facility isolation throughout sensitive workflows
- Production observability with request IDs and privacy-safe aggregate runtime metrics
- Patient-controlled sensitive disease disclosure with digital consent
- Support for SHA Treat Abroad (overseas treatment) workflows

## Repository structure

```text
afasync/
├── backend/
├── frontend/
├── docs/
├── docker-compose.yml
├── render.yaml
└── .github/
```

## Development principles

- One person = one AfyaSync ID.
- Coverage is separate from identity.
- Every clinical and financial event belongs to an encounter where applicable.
- Facility access is isolated and permission-controlled.
- National permissions are explicit and do not bypass facility staff assignment requirements.
- Important actions are audited.
- Medical and financial history is preserved rather than silently deleted.
- External integrations must be authorised and resilient to temporary failures.
- Production secrets are never committed to Git.
- Schema changes are applied through Alembic rather than application startup table creation.
- Healthcare delivery must remain usable without a payer integration being available.
- Operational telemetry must not contain patient payloads or patient identifiers.
- Sensitive clinical information is only shareable across facilities when the patient has given explicit digital consent.

## Main care and financing flow

`LOGIN → FACILITY → PATIENT → ENCOUNTER → CLINICAL SERVICES → BILLING → PAYMENT`

Coverage-enabled financing extends through:

`VERIFY → BENEFITS → PREAUTH → TREAT → CAPTURE → CLAIM → PAYER RESPONSE → REWORK → PAYMENT → RECONCILIATION`

## Production documentation

- `docs/PRODUCTION_DEPLOYMENT.md` — deployment topology, configuration, migrations, backups, rollback, and smoke testing
- `docs/PRODUCTION_OPERATIONS.md` — operational checks and incident handling
- `docs/PILOT_READINESS_CHECKLIST.md` — governance, security, clinical, financing, integration, and go-live checks
- `docs/NATIONAL_SECURITY_RELIABILITY.md` — national security and reliability controls
- `docs/PRODUCTION_PILOT_RUNBOOK.md` — deployment, onboarding, integration testing and pilot gates
- `docs/ROADMAP_11_15.md` — engineering gates through item 22

## Security

AfyaSync is intended for regulated healthcare use. Production deployment requires appropriate legal, regulatory, privacy, security, licensing, accreditation, payer, and integration review before real patient data is used.

## Copyright & Ownership

© 2026 AfyaSync. Developed by Bahati GAD. All rights reserved.

This software and its associated documentation are the intellectual property of Bahati GAD.  
Any unauthorized use, copying, modification, distribution, reverse engineering, or commercial exploitation is strictly prohibited and will be subject to legal action under the laws of Kenya and applicable international treaties.
