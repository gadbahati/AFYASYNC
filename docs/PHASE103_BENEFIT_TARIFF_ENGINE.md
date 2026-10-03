# Phase 103 — Universal Benefits & Tariff Engine

**Developer:** BAHATI GAD WANGWE

## Purpose

Single pricing/benefit truth under eligibility, preauthorization, claims and payments:

```
Service line + payer/plan + date
  → most specific ACTIVE rule
  → tariff ceiling + payer % + copay + caps
  → payer amount / patient amount / preauth flag
```

## APIs

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/benefit-engine/rules` | Create versioned rule |
| GET | `/api/v1/benefit-engine/rules` | List / filter |
| POST | `/api/v1/benefit-engine/quote` | Single-line quote + explanation |
| POST | `/api/v1/benefit-engine/quote-batch` | Multi-line (claims input) |

## Matching priority

1. Exact `service_code` + plan-specific rule  
2. Exact `service_code` + plan-agnostic  
3. `service_type` + plan-specific  
4. `service_type` + plan-agnostic  
5. Higher `version` wins ties  

## Decisions

- `ELIGIBLE` — covered under rule  
- `CONDITIONAL` — requires preauth  
- `INELIGIBLE` — excluded service  
- `UNKNOWN` — no matching ACTIVE rule (patient pays until configured)  

## Relation to SHA / DHA

This engine does not replace SHA; it provides **facility- and payer-side rule execution** that can later map to national benefit packages and EDI claim lines.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
