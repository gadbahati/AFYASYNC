"""add concurrency-safe human-facing identity sequence

Revision ID: 0015_identity_sequences
Revises: 0014_audit_logs
"""

from alembic import op
import sqlalchemy as sa

revision = "0015_identity_sequences"
down_revision = "0014_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE afasync_patient_id_seq START WITH 1 INCREMENT BY 1 MINVALUE 1")
    op.execute(
        """
        SELECT setval(
            'afasync_patient_id_seq',
            COALESCE(MAX(CAST(SUBSTRING(afya_id FROM 4) AS BIGINT)), 0),
            true
        )
        FROM afya_identities
        """
    )


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS afasync_patient_id_seq")
