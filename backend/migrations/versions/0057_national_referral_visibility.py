"""Reserve the national referral visibility migration revision.

Revision ID: 0057_national_referral_visibility
Revises: 0056_merge_national_supply_heads

The RBAC seed is intentionally deferred from the deployment transaction. The
schema migration must remain non-blocking so a fresh production instance can
start its API and health/readiness endpoints reliably. The permission and role
are provisioned separately once the service is live.
"""

from alembic import op

revision = "0057_national_referral_visibility"
down_revision = "0056_merge_national_supply_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Deliberately schema-neutral; RBAC provisioning is deferred until after
    # the API is live so deployment startup cannot be blocked by RBAC locks.
    pass


def downgrade() -> None:
    pass
