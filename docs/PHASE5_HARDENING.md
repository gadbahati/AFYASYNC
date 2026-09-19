# Phase 5 complete + hardening

**Developer:** Bahati GAD Wangwe  
**Scope:** Patient portal depth, facility respond/inbox, security and validation hardening.

## Delivered

### Patient portal
- Book appointment (any active facility) → request lifecycle
- Messages (two-way with facilities)
- My visits (list + encounter summary)
- Sensitive disclosure (view + change with digital signature)
- My coverage (SHA / membership summary)
- Styled with `portal.css` design system

### Facility
- Appointments page: **Incoming patient requests** (Accept / Propose time / Decline)
- **Messages** page (`/messages`): inbox + reply threads
- Sidebar link under Patients & care

### Hardening
- Reason/message length limits
- Max pending appointment requests per patient+facility (10)
- Reject offered appointment times in the past
- Department must belong to responding facility
- Related request id validated against patient + facility
- Empty message rejected
- Staff notifications for new requests and patient messages
- Audit events: request created/responded/cancelled, messages sent
- Patient actions scoped to `person_id`; facility actions require facility context

## Production checklist (before go-live)
1. Run Alembic migrations for `appointment_requests` and `facility_messages` (or `create_all` in non-prod).
2. Configure real SMS/email for password-reset codes.
3. Set `VITE_API_BASE_URL` and CORS origins.
4. Confirm JWT secrets and production `environment=production`.
5. Seed ACTIVE facilities and departments so booking can create appointments.

## Ready for Phase 6
Suggested Phase 6 themes: Treat Abroad staff UI, SHA claims preflight polish, or production SMS gateway integration.
