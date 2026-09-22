# National Phase 12 — Offline Resilience & Edge Operations

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## Contract (locked)
- No fabricated clinical results, eligibility, or claim payments offline
- External work goes to **outbox** with idempotency keys
- Drain validates then marks SYNCED (ready for online relay) — not “SHA paid”

## Delivered
| API | Purpose |
|-----|---------|
| `POST /api/v1/offline/enqueue` | Queue CLAIM_SUBMIT / ELIGIBILITY_CHECK / HIE_EXPORT / … |
| `POST /api/v1/offline/drain` | Process pending with retry backoff |
| `GET /api/v1/offline/pending` | List queue |
| `GET /api/v1/offline/stats` | By-status counts |
| `POST /api/v1/offline/connectivity-probe` | Edge connectivity log |

**Migration:** `0087_offline_outbox` → run `alembic upgrade head`

## Stakeholder value
- **Hospitals:** keep operating when WAN is down
- **Government:** clean, auditable sync — no silent claim invention
- **Individuals:** care continues; billing/eligibility reconciles when online

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
