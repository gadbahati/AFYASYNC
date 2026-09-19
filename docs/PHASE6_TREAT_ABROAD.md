# Phase 6 — Treat Abroad (facility UI)

**Developer:** BAHATI GAD WANGWE

## What was delivered

### Facility workspace
- Sidebar: **Treat Abroad** → `/treat-abroad`
- List SHA-approved overseas procedures (auto-seeded if empty)
- Create a case for a facility patient (DRAFT)
- Advance status along the allowed state machine:
  - DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED / REJECTED
  - APPROVED → TRAVEL_ARRANGED → TREATMENT_IN_PROGRESS → RETURNED → CLOSED

### Backend
- Referring clinician is always the authenticated staff member at the current facility
- Procedure catalogue seeds a representative SHA overseas subset on first load
- Cases scoped to facility context

## Hardening

| Control | Detail |
|---------|--------|
| Facility context | Procedures list + all case APIs require facility token |
| Patient check | Patient must exist and be ACTIVE |
| Procedure check | Must be active SHA-approved procedure |
| Open case limit | Max 20 non-closed/non-rejected cases per patient |
| Text limits | Summary 20–8000 chars; local reason 10–4000 |
| Status machine | No self-loops; CLOSED is terminal |
| CLOSED lock | No further updates once CLOSED |
| Amount cap | Approved KES cannot exceed procedure max_cover |
| Audit | Create + update with previous_status |
| Clinician binding | Always facility staff of caller |

## How to use
1. Sign in as **facility staff** and select a facility
2. Open **Treat Abroad** in the sidebar
3. Choose patient + approved procedure, enter clinical summary and local unavailability reason
4. Create case, then use action buttons to move status forward

## Next phases (suggested)
- Phase 7: SMS/email for password reset
- Phase 8: SHA claims UX polish
- Phase 9: Production migrations & deploy
