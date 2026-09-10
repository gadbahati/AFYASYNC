# Database migrations

AfyaSync uses Alembic for versioned PostgreSQL schema migrations.

Run migrations from the `backend` directory:

```bash
alembic upgrade head
```

For local development, the API can create development tables automatically. Before production, Alembic migrations must be the authoritative schema mechanism.

Never place real patient information in migration fixtures or test data.
