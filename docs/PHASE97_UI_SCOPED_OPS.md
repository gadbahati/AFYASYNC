# Phase 97 — UI scope wiring (referrals, appointments, billing)

**Developer:** BAHATI GAD WANGWE

## Pages

| Page | Scope-aware loads |
|------|-------------------|
| Referrals | `listReferrals`, `listTransfers`, `listPatients` |
| Appointments | `listAppointments`, `listPatients` |
| Billing | `listBillingServices`, `listInvoices`, `listPatients` |

Changing the sidebar **OPERATING SCOPE** reloads these lists automatically.

## Client fix

`listTransfers` now calls `/api/v1/referrals/transfers` (not the incorrect `/api/v1/transfers` path).

© 2026 AfyaSync. Developed by **BAHATI GAD WANGWE**.
