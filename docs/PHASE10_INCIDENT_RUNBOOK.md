# Phase 10 — Incident runbook (HARDENED)

**Developer:** BAHATI GAD WANGWE  
**Use during:** Pilot week and production

---

## Severity

| Level | Meaning | Response time target |
|-------|---------|----------------------|
| **P1** | System down, data loss risk, confirmed PHI leak, wrong-patient care risk | Immediate |
| **P2** | Major feature broken (login, claims submit, portal book) for all users | < 2 hours |
| **P3** | Degraded / single facility / workaround exists | Same business day |
| **P4** | Cosmetic / documentation | Planned |

---

## Contacts (fill before pilot)

| Role | Name | Phone | Channel |
|------|------|-------|---------|
| Incident commander | | | |
| Facility clinical lead | | | |
| Facility IT / admin | | | |
| AfyaSync technical | BAHATI GAD WANGWE / delegate | | |
| Hosting provider support | | | |
| Database / backup owner | | | |

---

## First 15 minutes (any P1/P2)

1. **Declare** severity and assign incident commander.  
2. **Capture evidence:** time, URL, user role, `X-Request-ID` if present, screenshots.  
3. **Check:** `GET /health`, `GET /ready` (note `alembic_revision`, `missing_tables`).  
4. **Check:** hosting dashboard (API, worker, DB CPU/storage).  
5. **Do not** delete databases, force-push Git, or hand-edit `alembic_version`.  
6. **Communicate** to facility: status + whether care should continue on paper/cash workflow.

---

## Common failure paths

### API not ready / missing tables

- Symptom: `/ready` 503, `missing_tables` listed.  
- Action: run `alembic upgrade head` against **this** database; re-check `/ready`.  
- Do not use `create_all` in production.

### Auth failures spike

- Check `JWT_SECRET` not rotated without logging everyone out intentionally.  
- Check clock skew on servers.  
- Confirm CORS origin exact match (scheme + host + port).

### Patient cannot register/login

- Confirm API URL on frontend.  
- Confirm patient auth routes deployed.  
- Check DB connectivity; no dummy test accounts expected.

### Claims / integration stuck

- Freeze **external** payer submission if payload integrity unknown.  
- Inspect worker logs and pending queue.  
- Resume only after reconciliation plan.

### Suspected PHI exposure

1. Contain (revoke tokens / disable public routes if needed).  
2. Preserve logs.  
3. Notify privacy owner and follow organisational breach process.  
4. Do not post PHI in tickets or chat.

---

## Rollback

1. Prefer **application version rollback** to last known good if schema compatible.  
2. Schema downgrades only with tested Alembic path and backup restore point.  
3. After rollback: UAT-01, UAT-02, UAT-07 smoke minimum.

Full restore: `docs/DISASTER_RECOVERY.md`.

---

## Post-incident (mandatory for P1/P2)

Within 5 business days:

- [ ] Timeline of events  
- [ ] Root cause  
- [ ] Data impact (yes/no PHI)  
- [ ] Fix shipped / workaround  
- [ ] Preventive action  
- [ ] Update this runbook if gaps found  

---

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
