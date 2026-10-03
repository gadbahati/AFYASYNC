# Phase 106 — Preauthorization workflow (benefit-engine driven)

**Developer:** BAHATI GAD WANGWE

## Flow

```
Benefit quote CONDITIONAL / requires_preauth
  → POST /api/v1/financing-preauthorizations  (PENDING)
  → POST .../{id}/decision  (AUTHORIZED | REJECTED | CONDITIONAL)
  → claims preflight: missing AUTHORIZED preauth → error
```

## APIs

| Method | Path |
|--------|------|
| POST | `/api/v1/financing-preauthorizations` |
| GET | `/api/v1/financing-preauthorizations?status=&person_id=` |
| POST | `/api/v1/financing-preauthorizations/{id}/decision` |

## Claims gate (preflight)

When a line needs preauth (`BENEFIT_PREAUTH_REQUIRED`):

- If no `AUTHORIZED`/`CONDITIONAL` financing preauth for person+payer+service → **error** `PREAUTH_REQUIRED:{code}`
- Warning retained for visibility; hard block prevents submit without approval

## Evidence

Request stores benefit quote + eligibility snapshots in `evidence` JSONB.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
