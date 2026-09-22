# National Phase 1 — Afya Identity & Membership (REPORT)

**Status:** Implemented (core gate) — hardening tests must be run in CI before pilot  
**Developer:** BAHATI GAD WANGWE  
**Migration:** `0078_identity_membership`

---

## Built (per programme guidelines)

| Requirement | Delivery |
|-------------|----------|
| Afya ID / person registry | Existing + gated create |
| Identity Confidence Engine | `POST /api/v1/identity/match` + create_patient gate |
| Household + dependants | households / household_members |
| Family relationships | relationship_to_head codes |
| Membership status | membership_records |
| Contribution history | contribution_entries |
| Employer relationship | employer_name / employer_pin on membership |
| Payer relationship | optional payer_id FK |
| Identity correction | request + maker-checker approve |
| Deceased handling | mark deceased + identity status DECEASED |
| Identity audit | match logs + audit actions |

**Not fully in this slice (deferred with structure):** offline registration sync queue, membership transfers workflow UI, assisted-registration multi-step UI, full impersonation red-team suite in CI.

---

## Beast feature — Identity Confidence Engine

Evidence codes: `NATIONAL_ID_EXACT`, `AFYA_ID_EXACT`, `MEMBERSHIP_EXACT`, `PHONE_NAME_EXACT`, `PHONE_SURNAME`, `DOB_NAME_EXACT`.

| Outcome | Score | Behaviour |
|---------|------:|-----------|
| BLOCK | ≥90 | Cannot create; use existing Afya ID |
| REVIEW | ≥55 | Requires force reason ≥20 chars + audit |
| CLEAR | <55 | Create allowed |

No raw national ID stored in match logs.

---

## APIs

| Method | Path |
|--------|------|
| POST | `/api/v1/identity/match` |
| POST | `/api/v1/identity/households` |
| POST | `/api/v1/identity/households/{id}/members` |
| POST | `/api/v1/identity/memberships` |
| GET | `/api/v1/identity/memberships/person/{id}` |
| POST | `/api/v1/identity/contributions` |
| POST | `/api/v1/identity/deceased` |
| POST | `/api/v1/identity/corrections` |
| POST | `/api/v1/identity/corrections/{id}/review` |

---

## Hardening checklist (run before Phase 2)

| Test | Expected |
|------|----------|
| Duplicate national ID | BLOCK / DUPLICATE |
| Same phone+name | REVIEW or BLOCK |
| Create after BLOCK without override | 409 |
| REVIEW override <20 chars | 409 |
| Self-approve correction | 403 CANNOT_SELF_APPROVE |
| Mark deceased twice | 409 |
| Add member already in other household | 409 |
| Concurrent create same ID | Integrity / conflict |

Deploy: `alembic upgrade head` (0078).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
