"""add concurrency-safe encounter sequence

Revision ID: 0016_encounter_sequence
Revises: 0015_identity_sequences
"""

from alembic import op

revision = "0016_encounter_sequence"
down_revision = "0015_identity_sequences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE afasync_encounter_seq START WITH 1 INCREMENT BY 1 MINVALUE 1")
    op.execute(
        """
        SELECT setval(
            'afasync_encounter_seq',
            COALESCE(MAX(CAST(SUBSTRING(encounter_id FROM 14) AS BIGINT)), 0),
            true
        )
        FROM encounters
        WHERE encounter_id ~ '^ENC-[0-9]{8}-[0-9]+$'
        """
    )


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS afasync_encounter_seq")
