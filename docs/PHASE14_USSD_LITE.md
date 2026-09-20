# Phase 14 — USSD + low-bandwidth access (HARDENED)

**Developer:** BAHATI GAD WANGWE  
**Status:** Implemented + hardened

---

## Channels

| Channel | Path | Purpose |
|---------|------|--------|
| USSD callback | `POST /api/v1/ussd/callback` | Feature-phone menus (AT-style CON/END) |
| Set PIN | `POST /api/v1/ussd/pin` | Patient portal sets 4–6 digit USSD PIN |
| Lite HTML | `GET /api/v1/lite` | Minimal page for slow data |

Migration: **`0075_ussd_sessions`** (`ussd_pins`, `ussd_sessions`).

---

## USSD flow

1. Phone must match a registered patient `persons.phone`  
2. First use → create PIN  
3. Later → enter PIN (lock after 5 failures for 30 minutes)  
4. Menu: appointments · continuity prefix · book visit · Afya ID  

**No clinical free-text or sensitive diagnoses on USSD.** Continuity shows prefix only.

---

## Hardening

| Control | Detail |
|---------|--------|
| HMAC webhook | Required in production (`X-AfyaSync-Timestamp` + `X-AfyaSync-Signature`) |
| PIN | SHA-256 with person-scoped material; never stored plain |
| Session TTL | 5 minutes |
| Rate limit | Soft cap by phone sessions / hour |
| Form + JSON | Africa’s Talking form fields or JSON body |

Env: `USSD_WEBHOOK_SECRET` (required in production).

---

## Deploy

```bash
alembic upgrade head
# set USSD_WEBHOOK_SECRET in production
```

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
