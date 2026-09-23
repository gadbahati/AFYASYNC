# National Phase 36 — National Change-Control & Release Governance

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## APIs

| Path | Purpose |
|------|---------|
| `GET /api/v1/change-control/policy` | Governance rules |
| `POST/GET /api/v1/change-control/changes` | Create / list change requests |
| `POST .../changes/{id}/transition` | Status machine |
| `POST/GET /api/v1/change-control/releases` | Release registry |

**Migration:** `0095_change_control`

## Honest limit
In-app governance ledger — not ServiceNow/Jira replacement.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
