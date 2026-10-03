# Phase 109 — Adjudication auto-obligation + claims workbench restore

**Developer:** BAHATI GAD WANGWE

## Auto settlement obligation

When `adjudicate()` finishes with `APPROVED` or `PARTIALLY_APPROVED` and `allowed_amount > 0`:

1. Calls `generate_obligation(...)` for the claim  
2. Audits `AUTO_SETTLEMENT_OBLIGATION` with result `SUCCESS` / `SKIPPED` / `ERROR`  

Idempotent: existing obligation is returned by settlement service.

## Claims UI

Full claims workbench restored in `ClaimsPageBody.tsx` (preflight benefit engine counters retained).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
