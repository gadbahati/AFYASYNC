# AFYASYNC Step 7 — System-wide security & integrity review

Date: 2026-09-11  
Scope: Backend API isolation, RBAC, audit, callbacks, patient portal ownership.

## Architecture rules verified

1. **Facility isolation** — clinical, billing, claims, lab, pharmacy, referrals, appointments enforce facility context from the access token (not trusted client body fields alone).
2. **Server-side RBAC** — `require_permission` + active staff membership at the facility.
3. **Enrollment** — encounters and coverage registration require active `PatientFacility` membership.
4. **Audit** — sensitive creates/reads/status changes write audit events.
5. **Patient portal** — ownership via `user.person_id` only; no cross-patient access.
6. **Integration callbacks** — HMAC signature + timestamp validation on payer/payment callbacks (no bearer auth by design).

## Findings fixed in this step

| Issue | Severity | Fix |
|-------|----------|-----|
| `POST /coverage` had no permission check | High | Requires `coverage.write` + facility context + patient enrollment |
| Staff could not lawfully read patient coverage without over-sharing patient endpoint | Medium | Added `GET /coverage/facility/person/{id}/active` with `coverage.read` + enrollment |
| Patient self coverage endpoint remained ownership-scoped | OK | Unchanged: only own `person_id` |
| Appointments accepted client `facility_id` then compared | Medium | Facility ID always overwritten from token context |
| Appointment list used write permission for reads | Low | Switched list to `appointments.read` |

## Modules reviewed as already aligned

- Patients, encounters, clinical timeline, portal
- Laboratory (granular lab.* permissions)
- Pharmacy (granular pharmacy permissions)
- Billing / claims (facility + permission + idempotency on payments)
- Referrals/transfers (source or destination facility access)
- Integrations callbacks (signature verification)
- Notifications (user_id ownership)

## Residual risks / follow-ups (Step 8+)

1. Seed/migrate all permission codes used by routers into the `permissions` table and default roles.
2. Ensure CI runs the full pytest suite on every push to `main`.
3. Production: disable `create_all` on startup; rely on Alembic only.
4. Rate-limit auth login and callback endpoints at the edge.
5. Consider binding coverage benefit-rule writes to facility/payer authorization policy beyond a single permission code.

## Conclusion

No redesign was performed. Highest-priority integrity gaps found in coverage and appointments were closed while preserving the existing architecture.
