"""add preauthorization idempotency key

Revision ID: 0018_preauthorization_idempotency
Revises = 0017_national_benefit_network_permissions
"""

from alembic import op
import sqlalchemy as sa

revision = "0018_preauthorization_idempotency"
down_revision = "0017_national_benefit_network_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("preauthorizations", sa.Column("idempotency_key", sa.String(length=150), nullable=True))
    op.create_unique_constraint(
        "uq_preauthorization_facility_idempotency",
        "preauthorizations",
        ["facility_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_preauthorization_facility_idempotency", "preauthorizations", type_="unique")
    op.drop_column("preauthorizations", "idempotency_key")
