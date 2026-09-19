# Treat Abroad — SHA Overseas Treatment

**Developed by Bahati GAD Wangwe**

## Purpose

Support the Social Health Authority’s overseas treatment package: a fixed list of procedures that cannot currently be done in Kenya, subject to pre-authorisation, a financial cap (KSh 500,000), and treatment only at contracted foreign hospitals.

## Status machine

```
DRAFT → SUBMITTED → UNDER_REVIEW → APPROVED / REJECTED
                                      ↓
                              TRAVEL_ARRANGED
                                      ↓
                          TREATMENT_IN_PROGRESS
                                      ↓
                                   RETURNED → CLOSED
```

Invalid transitions are rejected by the service layer.

## API

| Method | Path | Purpose |
|--------|------|--------|
| GET | `/api/v1/treat-abroad/procedures` | List SHA-approved overseas procedures |
| POST | `/api/v1/treat-abroad/cases` | Create a new overseas treatment case |
| GET | `/api/v1/treat-abroad/cases` | List cases for current facility |
| GET | `/api/v1/treat-abroad/cases/{id}` | Get one case |
| PATCH | `/api/v1/treat-abroad/cases/{id}` | Update status, SHA refs, travel dates, follow-up |

## Key fields captured

- Clinical summary and reason the procedure is unavailable in Kenya
- Referring clinician
- SHA pre-auth reference and commitment letter reference
- Approved amount (KES)
- Foreign hospital name, city, country
- Departure, treatment, and return dates
- Follow-up facility and notes in Kenya

## Design principles

- Only procedures in the approved catalogue can be selected.
- Facility isolation is enforced on all case operations.
- Every create and status change is audited.
- The module is ready to attach real SHA pre-auth / remittance callbacks when official APIs are available.

## Seed data

A representative subset of procedures is seeded (liver transplant, bone marrow transplant, complex paediatric cardiac surgery, complex joint reconstruction, complex neurosurgery). The full gazetted list of 36 can be loaded into the same table later.
