# National Phase 13 — Analytics, Fraud Signals & Public-Health Reporting

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## Delivered

| API | Purpose |
|-----|---------|
| `GET /api/v1/analytics/fraud/facility` | Rule-based fraud signals |
| `GET /api/v1/analytics/public-health/facility` | De-identified aggregates |
| `GET /api/v1/analytics/claims/kpis` | Pipeline + denial rate |
| `GET /api/v1/analytics/overview` | Combined snapshot |

Also retains existing: `/api/v1/insight/fraud-radar`, command-centre, national reports.

## Fraud rules (examples)
- Multiple claims same invoice (HIGH)
- High claim frequency per patient (MEDIUM)
- High-value open invoices (MEDIUM)
- Zero-amount claims (LOW)
- Encounters without charges (MEDIUM)

## Privacy
Public-health payload = **codes and counts only** — no patient names/IDs.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
