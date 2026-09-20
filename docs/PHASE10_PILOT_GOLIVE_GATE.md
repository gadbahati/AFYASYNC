# Phase 10 — Pilot / go-live gate (HARDENED)

**Developer:** BAHATI GAD WANGWE  
**Status:** Active — must pass before Phase 11 (rejection prevention)  
**Depends on:** Phase 9 migrations (`0071` + `0072`), production deploy controls

---

## Purpose

Prove AfyaSync can run a **real facility pilot week** without emergency patches, dummy credentials, or untested recovery.

This phase is a **gate**, not a feature dump. No Phase 11+ work until exit criteria are signed.

---

## Hardening principles

| Rule | Enforcement |
|------|-------------|
| No dummy logins | Patient self-register only; no AFYA-TEST accounts |
| No `create_all` in production | Alembic only (`alembic upgrade head`) |
| Schema proof | `GET /ready` returns ready + revision; no `missing_tables` |
| Sandbox claims | Sandbox reject **blocked** when `ENVIRONMENT=production` |
| Admin seed | `SEED_UNIVERSAL_ADMIN` forbidden in production without `BOOTSTRAP_UNIVERSAL_ADMIN_ONCE` |
| Secrets | Never in Git; JWT ≥ 32 chars; CORS exact HTTPS origins |
| PHI | No clinical payloads in browser service-worker cache |
| Three owners | Clinical + security/privacy + facility admin must sign go-live |

---

## A. Pre-pilot infrastructure (blockers)

- [ ] Managed PostgreSQL provisioned (not local SQLite)
- [ ] Automated **encrypted** backups enabled
- [ ] **Restore test completed** within last 30 days (see `DISASTER_RECOVERY.md`)
- [ ] TLS end-to-end (frontend HTTPS → API HTTPS)
- [ ] `ENVIRONMENT=production`
- [ ] `JWT_SECRET` generated outside Git (≥ 32 random chars)
- [ ] `CORS_ORIGINS` = exact frontend origin(s) only
- [ ] `VITE_API_BASE_URL` = production API (no trailing slash)
- [ ] `alembic current` shows **`0072_seed_overseas_procedures`** (or later)
- [ ] `GET /health` → healthy
- [ ] `GET /ready` → ready, `database: ok`, no `missing_tables`
- [ ] Integration worker running if claims/integrations enabled
- [ ] SMS/EMAIL providers documented (`console` allowed only if pilot accepts no real SMS)

---

## B. Security gate (blockers)

- [ ] Named staff accounts only (no shared passwords)
- [ ] Facility isolation tested (Facility A staff cannot read Facility B patients)
- [ ] Patient token cannot open facility shell (`ProtectedRoute` redirects to `/portal`)
- [ ] Staff token without facility redirected to facility select
- [ ] Password reset codes hashed at rest; single-use; expiry enforced
- [ ] Audit events present for: patient register, login, consent change, claim submit
- [ ] Logs reviewed — no passwords, full ID numbers, or signature blobs in plain logs
- [ ] Claims sandbox-reject returns error in production

---

## C. UAT evidence (must attach or log results)

Run **`docs/PHASE10_UAT_SCRIPT.md`** end-to-end. Minimum pass:

| ID | Scenario | Pass? |
|----|----------|-------|
| UAT-01 | Entry → facility login → select facility → dashboard | |
| UAT-02 | Patient create account → portal home | |
| UAT-03 | Patient book appointment → facility sees request → accept/decline | |
| UAT-04 | Patient ↔ facility message round-trip | |
| UAT-05 | Staff: patient register → encounter → diagnosis (optional consent path) | |
| UAT-06 | Cash path works with SHA offline (no hard dependency) | |
| UAT-07 | Invoice → claim preflight → validate (no sandbox in prod) | |
| UAT-08 | Treat Abroad: procedures list non-empty → create DRAFT case | |
| UAT-09 | Patient password reset request does not leak whether account exists | |
| UAT-10 | Wrong password / wrong facility isolation fails closed | |

**Hardening rule:** Any failed UAT-01…10 is a **go-live blocker**.

---

## D. Clinical & financing pilot scope

Define in writing before pilot week:

| Item | Decision |
|------|----------|
| Pilot facility name / code | |
| Modules in scope | e.g. registration, encounters, portal booking, claims prep |
| Modules out of scope | e.g. theatre, blood bank if not staffed |
| SHA live API | Sandbox only / production credentials / offline |
| Support hours | |
| Escalation contacts | |

---

## E. Operations during pilot week

Daily (or each shift):

- [ ] `/ready` green
- [ ] Error rate review (5xx, auth failures)
- [ ] Integration queue (if used): pending / failed
- [ ] Backup job succeeded last 24h

On any P1 (system down, data corruption suspicion, PHI leak):

1. Follow **`docs/PHASE10_INCIDENT_RUNBOOK.md`**
2. Freeze claim submission to external payers if integrity uncertain
3. Preserve logs + request IDs

---

## F. Go-live / pilot approval sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Facility clinical lead | | | |
| Facility admin / IT | | | |
| Security / privacy owner | | | |
| AfyaSync technical owner (**BAHATI GAD WANGWE** or delegate) | | | |

**Statement:** Passing this gate authorises a **time-boxed pilot**. It is **not** statutory national certification or SHA product approval.

---

## G. Exit criteria → Phase 11

All must be true:

1. Sections A–B complete  
2. UAT-01…10 passed and recorded  
3. Restore drill evidenced (date + result)  
4. Incident runbook contacts filled  
5. Sign-off table complete  
6. No open P1/P2 defects without workaround  

Then: **Phase 11 — SHA rejection prevention engine**.

---

## Related docs

- `docs/PHASE9_PRODUCTION_DEPLOY.md` — migrations & env  
- `docs/PHASE10_UAT_SCRIPT.md` — step-by-step tests  
- `docs/PHASE10_INCIDENT_RUNBOOK.md` — incidents  
- `docs/DISASTER_RECOVERY.md` — backup/restore  
- `docs/PILOT_READINESS_CHECKLIST.md` — broader governance list  
- `docs/PRIVACY_DATA_GOVERNANCE.md` — consent & DPA  

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**. Unauthorised copying of design or code is prohibited.
