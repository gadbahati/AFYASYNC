# Security hardening — Phases 1 to 5

**Platform:** AfyaSync  
**Developer:** Bahati GAD Wangwe

This document records the security and integrity controls applied across Phases 1–5.

---

## Phase 1–2 — Sensitive consent & Treat Abroad

| Control | Detail |
|---------|--------|
| Safe default | No consent record → diagnosis **not** shareable across facilities |
| Signature required | Recording or changing consent requires signature proof (min length enforced) |
| One consent per diagnosis | Duplicate consent rows rejected |
| Audit | `SENSITIVE_DISEASE_CONSENT_RECORDED`, `PORTAL_CONSENT_UPDATED` |
| Treat Abroad transitions | Strict status state machine; invalid transitions rejected |
| Facility isolation | Cases scoped by facility where required |

---

## Phase 3 — Branding & IP

| Control | Detail |
|---------|--------|
| Copyright | Footer, README, NOTICE — Bahati GAD Wangwe |
| Anti-theft notice | Unauthorized use prohibited under Kenyan/international law |

---

## Phase 4 — Patient auth & portal identity

| Control | Detail |
|---------|--------|
| Real identity | Register only if Afya ID already exists in system |
| Login | Afya ID or SHA membership + password |
| Rate limiting | Auth endpoints use `enforce_auth_rate_limit` |
| Token model | Patient tokens issued with **no facility_id** |
| Credential enumeration | Login failures return generic `INVALID_CREDENTIALS` |
| Reset codes | Hashed at rest; 15-minute TTL; prior unused tokens invalidated |
| Reset response | Does not reveal whether identifier exists (except missing phone/email channel) |
| Production | Reset code never returned in API body |

---

## Phase 5 — Portal depth, booking, messaging

| Control | Detail |
|---------|--------|
| Patient token guard | `require_patient_identity` — person_id required; staff facility tokens blocked from portal APIs |
| Facility context | Staff booking/message APIs require `require_facility_context` |
| Data scoping | Portal only returns the authenticated patient's own records |
| Booking limits | Max 10 pending requests per patient per facility |
| Time validation | Offered appointment cannot be in the past |
| Message limits | Max length; empty body rejected |
| Related request | Must match patient + facility |
| Audit | Request create/respond/cancel; message send; portal views |
| Frontend | `ProtectedRoute` redirects patient sessions away from facility workspace |

---

## Cross-cutting

- Security headers middleware (nosniff, frame deny, HSTS in production)
- JWT access + refresh with rotation / family revoke on reuse
- CORS restricted to configured origins
- Request IDs on responses

---

## Remaining production ops (not code gaps)

1. Wire real SMS/email for password-reset delivery  
2. Alembic migrations for new tables in production  
3. Secrets management (JWT, DB) outside source control  
4. Penetration test before national rollout  

---

Phases 1–5 are **hardened for development and pilot**. Phase 6 can focus on Treat Abroad UI, SHA claims depth, or production messaging gateways.
