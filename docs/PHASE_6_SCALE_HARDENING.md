# Phase 6 — scale and national intelligence hardening

## Implemented
- National intelligence facility signals are bounded and paginated (default 100, maximum 500).
- Invalid pagination values are rejected at the API boundary.
- National report date windows remain explicit and half-open internally, preventing end-of-day ambiguity.
- National facility metadata enumeration is separated from time-window financial/clinical aggregates so the base facility scan does not accidentally multiply joined rows.
- Regression coverage protects date-window validation and intelligence pagination defaults.

## Remaining operational evidence
Before national scale-up, execute representative load tests against a production-like environment, confirm PostgreSQL indexes with query plans, validate connection-pool saturation under concurrency, and perform backup/restore drills. These are operational evidence gates and are not substituted by application code.
