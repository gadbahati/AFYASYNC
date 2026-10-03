# Phase 111 — Claims adjudication UI

**Developer:** BAHATI GAD WANGWE

## What landed

- Client: `api.adjudicateClaim(claimId, force?)` → `POST /api/v1/adjudication/run`
- Claims workbench **Adjudicate** action on DRAFT / READY / SUBMITTED / UNDER_REVIEW / REJECTED / ACCEPTED claims
- Success message shows decision, allowed amount, patient amount, reason code
- Payable decisions still trigger **auto settlement obligation** (Phase 109)

## Flow

```
Validate → Adjudicate → (AUTO_SETTLEMENT_OBLIGATION)
  → Settlements page: batch → pay → reconcile
```

## Smoke path (financing)

1. Benefit rule active for service  
2. Preflight invoice (preauth if CONDITIONAL)  
3. Create claim → Validate → Adjudicate  
4. Confirm READY obligation  
5. Settlement batch / payment  

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
