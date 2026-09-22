# National Phase 16 — Emergency & Referral Network Depth

**Status:** Core **PASSED**  
**Developer:** BAHATI GAD WANGWE

## APIs

| Path | Purpose |
|------|---------|
| `GET /api/v1/emergency-network/board` | Open ER visits (optional county) |
| `GET /api/v1/emergency-network/facility-load` | Local load band |
| `GET /api/v1/emergency-network/referral-destinations` | Suggested receivers by load |
| `GET /api/v1/emergency-network/overview` | Network KPIs |

Builds on existing emergency visits, referrals, transfers, national-referrals metrics.

## Honest limit
Routing is **advisory** — clinical judgment + receiving facility acceptance required.

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
