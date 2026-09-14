# National Operations

AfyaSync national operations are aggregate-only command-centre capabilities. National users receive operational, capacity, referral, supply, claims, payer and integration signals without unrestricted patient-level access.

## Operational surface

- `/api/v1/reports/national` — national financial and operational report
- `/api/v1/reports/national/operations` — current operational health summary
- `/api/v1/reports/national/intelligence` — national intelligence and risk signals
- `/api/v1/national/capacity` — facility capacity and queue aggregates
- `/api/v1/national/referrals` — referral network aggregates
- `/api/v1/national/supply` — supply visibility and planning

All national report routes require the explicit national reporting permission. Facility permissions do not implicitly grant national access.

## Data minimisation

National operational endpoints must not return patient identifiers, clinical narratives, diagnoses, contact information or unrestricted encounter records. Patient-level workflows remain facility-scoped unless a separate, explicitly authorised national capability exists.

## Reliability signals

The operations summary tracks open encounters, recent encounters, open invoices, pending prescriptions, low-stock items, rejected claims and pending/retrying/failed integration transactions. These are intended for operational triage, not clinical decision-making.
