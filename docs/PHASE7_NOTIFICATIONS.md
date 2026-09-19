# Phase 7 — Password reset delivery (SMS / email)

**Developer:** BAHATI GAD WANGWE

## What was delivered

Patient password-reset codes are delivered through a pluggable provider layer:

| Channel | Providers |
|---------|-----------|
| **SMS** | `console` (default), `http` (generic JSON gateway) |
| **Email** | `console` (default), `smtp` |

- Code is **never** returned in the HTTP response
- Destination is masked in the API (`***1234` / `ab***@domain`)
- Prior unused reset tokens are invalidated when a new code is issued
- Delivery failures are logged; the client still gets a generic success message (anti-enumeration)

## Hardening

| Control | Detail |
|---------|--------|
| Rate limit (all patient auth) | 20 req / 60s per IP + path |
| Rate limit (reset request) | **5 req / 5 min** per IP + path |
| Destination validation | E.164-ish phone; strict email regex |
| Code format | 4–8 digits only before send |
| SMS URL | **HTTPS required** in production |
| SMTP | **TLS required** in production |
| JSON body | Safe `json.dumps` (no string injection) |
| Production logs | Plain code never logged |
| API body | Code never returned |

## Configuration (environment variables)

```env
# SMS
SMS_PROVIDER=console          # or http
SMS_HTTP_URL=                 # required if SMS_PROVIDER=http; HTTPS in production
SMS_HTTP_API_KEY=             # optional Bearer token
SMS_SENDER_ID=AfyaSync

# Email
EMAIL_PROVIDER=console        # or smtp
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@afyasync.local
SMTP_USE_TLS=true             # required true in production
```

### Development
Leave providers as `console`. Reset codes appear in backend logs (non-production only).

### Production SMS
Point `SMS_PROVIDER=http` and `SMS_HTTP_URL` (HTTPS) at your Kenya SMS aggregator.

### Production email
Set `EMAIL_PROVIDER=smtp` and SMTP credentials with TLS.

## Flow
1. Patient requests reset with Afya ID / SHA number + channel (PHONE or EMAIL)
2. Server creates hashed 6-digit code (15 min TTL)
3. `deliver_password_reset_code` validates destination and sends via provider
4. Patient confirms code + new password
