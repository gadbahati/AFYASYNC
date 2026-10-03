# Phase 116 — Settlement auto-fill + claims KES risk banner

**Developer:** BAHATI GAD WANGWE

## Settlement page

- Loads READY obligations via `GET /settlements/obligations?status=READY`
- **Use** fills claim_id, payer_id, obligation_id, amount
- Overview stats: READY / in-batch / payments recorded
- Supports `?claim_id=` query param on page load

## Claims KES at risk

Banner on claims workbench from `claimsKesAtRisk(7)` — rejected, in-flight, draft/ready exposure.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
