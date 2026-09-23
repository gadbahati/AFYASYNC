# National Phase 38 — National Scale Load & Performance Acceptance

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## APIs

| Path | Purpose |
|------|---------|
| `GET /api/v1/performance/catalogue` | Targets + load scenarios |
| `GET /api/v1/performance/acceptance` | Evaluate vs runtime metrics |

## Targets
- Avg latency ≤ 1.5s
- Max latency ≤ 5s
- 5xx rate ≤ 1%
- Availability ≥ 99%

## Honest limit
Evaluates process metrics; **k6/Locust** must generate national-scale traffic externally.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
