# National Hardening Gate — Phases 11–20

**Developer:** BAHATI GAD WANGWE  
**Status:** HARDENED (code + schema alignment)

## Scope

| Phase | Module | Hardening applied |
|------:|--------|-------------------|
| 11–13 | offline / analytics / pilot | Existing outbox + evidence endpoints retained |
| 14 | pilot | Checklist / migration-readiness |
| 15 | logistics | Live inventory ratios only |
| 16 | emergency_network | `arrived_at` (not invented created_at); open ER statuses expanded |
| 17 | workforce | Credential status machine + expiry refresh |
| 18 | citizen_wallet | Fields aligned to Coverage.start/end, Charge.total_amount, Invoice.patient_amount |
| 19 | telemedicine | Status machine + one-open-request guard |
| 20 | ambulance | Strict status transitions + priority board |

## Migrations required

```bash
alembic upgrade head
# includes 0088 professional_credentials, 0089 tele_consult_requests, 0090 ambulance_requests
```

## Routers must be live on main

`offline`, `analytics`, `pilot`, `logistics`, `emergency_network`, `workforce`, `citizen_wallet`, `telemedicine`, `ambulance`

## Explicit non-dummies

- No fake GPS or video SDK
- No fake SHA national benefit balance
- Redistribution / referral routing are **advisory**
- Live SHA still needs your tokens (`SHA_DHA_MODE=live`)

## Smoke checklist

1. Patient: telemedicine request → facility respond → complete  
2. Patient: ambulance request → facility board → status DISPATCHED  
3. Patient: citizen-wallet/overview returns coverages or empty lists (not 500)  
4. Facility: logistics/stockout-board and emergency-network/board  
5. Facility: workforce/compliance  
6. Offline enqueue + drain stats  

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
