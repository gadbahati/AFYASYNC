# Patient Portal & Individual Viewing

**Developed by Bahati GAD Wangwe**

## Purpose

Give every patient secure, self-service access to their own health information, coverage status, and sensitive disease disclosure decisions — without exposing other people’s data.

## What the patient can see and do

| Capability | Endpoint | Notes |
|------------|----------|-------|
| Own profile | `GET /api/v1/portal/me` | Name, Afya ID, basic demographics |
| Own encounters | `GET /api/v1/portal/encounters` | List of visits |
| Encounter summary | `GET /api/v1/portal/encounters/{id}` | Vitals, consultation, diagnoses, labs, prescriptions (own only) |
| Own referrals | `GET /api/v1/portal/referrals` | Referral history |
| Sensitive disclosure decisions | `GET /api/v1/portal/consents` | See every consent they have given or declined |
| Change a disclosure decision | `PATCH /api/v1/portal/consents/{id}` | Requires new digital signature |
| Coverage / membership | `GET /api/v1/portal/coverage` | SHA / other coverage summary |

## Security rules

- The portal only works for users linked to a `person_id` (patient identity).
- Every view is audited (`PORTAL_VIEW_*` actions).
- A patient can only ever see **their own** records.
- Sensitive diagnoses appear in the patient’s own view (they have a right to see their data).
- Cross-facility visibility of sensitive diagnoses is still controlled by the consent recorded in Phase 2.

## Changing disclosure consent

A patient may later decide to share (or stop sharing) a sensitive diagnosis across facilities.

1. Patient opens their consent list.
2. Selects a previous decision.
3. Supplies a new on-screen signature and the new choice (`consent_given` true/false).
4. System updates `share_scope` and writes a full audit entry.

## Design principles

- Minimum necessary data in every response.
- No staff facility context is required for portal routes (patient is the actor).
- Portal never becomes a secondary clinical system for staff.

## Future extensions (not yet implemented)

- Appointment self-booking
- Prescription pickup status notifications
- Lightweight USSD / WhatsApp views of the same data
