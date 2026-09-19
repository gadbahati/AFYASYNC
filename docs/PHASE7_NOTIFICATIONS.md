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

## Configuration (environment variables)

```env
# SMS
SMS_PROVIDER=console          # or http
SMS_HTTP_URL=                 # required if SMS_PROVIDER=http
SMS_HTTP_API_KEY=             # optional Bearer token
SMS_SENDER_ID=AfyaSync

# Email
EMAIL_PROVIDER=console        # or smtp
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@afyasync.local
SMTP_USE_TLS=true
```

### Development
Leave providers as `console`. Reset codes appear in backend logs (non-production only).

### Production SMS
Point `SMS_PROVIDER=http` and `SMS_HTTP_URL` at your Kenya SMS aggregator
(Africa’s Talking, Safaricom, Twilio, etc.). The payload is:

```json
{ "to": "+254…", "message": "…", "from": "AfyaSync" }
```

### Production email
Set `EMAIL_PROVIDER=smtp` and SMTP credentials.

## Flow
1. Patient requests reset with Afya ID / SHA number + channel (PHONE or EMAIL)
2. Server creates hashed 6-digit code (15 min TTL)
3. `deliver_password_reset_code` sends via configured provider
4. Patient confirms code + new password

## Security notes
- Rate limited via existing auth rate limiter
- Production never logs the plain code
- HTTP body never includes the code
