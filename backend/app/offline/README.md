# Offline resilience (Phase 12)

**Developer:** BAHATI GAD WANGWE

AfyaSync does **not** invent clinical results, eligibility, or claim payments while offline.

## Contract

1. Local care workflows continue where domain rules allow.
2. External operations (SHA eligibility, claim submit, HIE export) go into the **outbox** with idempotency keys.
3. Drain marks events `SYNCED` only after validation — not after fake payer acceptance.
4. Live SHA/DHA still requires credentials (`SHA_DHA_MODE=live`).

## APIs

- `POST /api/v1/offline/enqueue`
- `POST /api/v1/offline/drain`
- `GET /api/v1/offline/pending`
- `GET /api/v1/offline/stats`
- `POST /api/v1/offline/connectivity-probe`

Run migration: `alembic upgrade head` (0087).
