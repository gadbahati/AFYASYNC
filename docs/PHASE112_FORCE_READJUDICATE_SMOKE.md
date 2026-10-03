# Phase 112 — Force re-adjudicate + financing smoke path

**Developer:** BAHATI GAD WANGWE

## APIs

| Method | Path |
|--------|------|
| POST | `/api/v1/adjudication/run` `{ claim_id, force }` |
| GET | `/api/v1/adjudication/claims/{claim_id}` |
| GET | `/api/v1/adjudication/claims/{claim_id}/lines` |

## UI

- **Adjudicate** — first run (`force=false`)
- **Re-adjudicate** — ACCEPTED/REJECTED claims (`force=true`), replaces prior adjudication rows

## Smoke checklist (financing 103–112)

1. [ ] Benefit rule ACTIVE for service code  
2. [ ] Coverage VERIFIED + ACTIVE for person/payer  
3. [ ] Preflight invoice — ready (preauth AUTHORIZED if CONDITIONAL)  
4. [ ] Create claim → Validate  
5. [ ] Adjudicate → decision + amounts in banner  
6. [ ] READY settlement obligation appears  
7. [ ] Settlement batch → payment → reconcile  
8. [ ] Re-adjudicate with force after rule change  
9. [ ] GET `/adjudication/claims/{id}/lines` shows line decisions  

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
