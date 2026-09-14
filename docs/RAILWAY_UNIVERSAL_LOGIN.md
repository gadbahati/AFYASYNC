# Railway: universal staff login (one-shot seed)

Do **not** set `ENVIRONMENT=development` to create the admin. That runs `create_all()` and can break a migrated Postgres schema (CITEXT / drift).

## Credentials (defaults)

| Field | Value |
|--------|--------|
| Username | `afyasync.admin` |
| Password | `Kenya@Health2026` |

Override with `UNIVERSAL_ADMIN_USERNAME` / `UNIVERSAL_ADMIN_PASSWORD` if you prefer.

## Steps on Railway

1. Deploy latest `main` (includes `app/scripts/seed_universal_admin.py`).
2. On the **API** service, set variables:
   - `SEED_UNIVERSAL_ADMIN=1`
   - `SEED_RESET_PASSWORD=1` (first time, so password is applied even if a partial user exists)
   - optional: `UNIVERSAL_ADMIN_USERNAME`, `UNIVERSAL_ADMIN_PASSWORD`
3. Redeploy once.
4. Check deploy logs for: `SEED_UNIVERSAL_ADMIN: {...}`
5. Log in on the frontend with the credentials above.
6. **Remove** `SEED_UNIVERSAL_ADMIN` and `SEED_RESET_PASSWORD` so later deploys do not keep resetting the password.

## What the seeder does

- `CREATE EXTENSION IF NOT EXISTS citext` (safe)
- Ensures pilot facility `AFYA-DEMO-001` (ACTIVE)
- Ensures person + user + staff assignment (ACTIVE)
- Does **not** call `Base.metadata.create_all()`
- Does not crash the API if seed fails (logs and continues)

## Alternative: one-shot shell (if Railway allows)

```bash
SEED_UNIVERSAL_ADMIN=1 SEED_RESET_PASSWORD=1 python -m app.scripts.seed_universal_admin --force
```

Keep `ENVIRONMENT=production` and a strong `JWT_SECRET`.
