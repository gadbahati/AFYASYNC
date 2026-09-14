"""add concurrency-safe human-facing identity sequence

Revision ID: 0015_identity_sequences
Revises: 0014_audit_logs
"""

from alembic import op

revision = "0015_identity_sequences"
down_revision = "0014_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE afasync_patient_id_seq START WITH 1 INCREMENT BY 1 MINVALUE 1")
    # PostgreSQL sequences cannot be set to zero when MINVALUE is 1.  On an
    # empty production database the first generated identity must therefore
    # start at 1 without being marked as already consumed; on a populated
    # database the existing highest numeric identity remains the last value.
    op.execute(
        """
        SELECT setval(
            'afasync_patient_id_seq',
            GREATEST(COALESCE(MAX(CAST(SUBSTRING(afya_id FROM 4) AS BIGINT)), 0), 1),
            COALESCE(MAX(CAST(SUBSTRING(afya_id FROM 4) AS BIGINT)), 0) > 0
        )
        FROM afya_identities
        """
    )


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS afasync_patient_id_seq")
