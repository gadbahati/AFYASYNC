# Phase 115 — CSV tariff upload + claim obligation lookup

**Developer:** BAHATI GAD WANGWE

## Settlement

`GET /api/v1/settlements/obligations?claim_id=&status=`

Client: `api.settlementListObligations({ claim_id?, status?, limit? })`

Claims workbench: **Obligation** action loads obligation for that claim.

## CSV tariff import

Benefits page accepts CSV with headers matching rule fields, converts to JSON array, then calls `importBenefitRules`.

Minimum columns: `benefit_package_id,payer_id,name,effective_from,service_code` (or `service_type`).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
