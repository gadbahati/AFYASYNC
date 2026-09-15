"""Repair the patient identity sequence in existing production databases.

Revision ID: 0059_repair_patient_identity_sequence
Revises: 0058_universal_admin_rbac
"""

from alembic import op

revision = "0059_repair_patient_identity_sequence"
down_revision = "0058_universal_admin_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Older/partially migrated production databases may have the migration
    # recorded while the sequence itself is absent or out of sync.  Repair it
    # idempotently before any new patient registration reaches nextval().
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_class
                WHERE relkind = 'S'
                  AND relname = 'afasync_patient_id_seq'
            ) THEN
                CREATE SEQUENCE afasync_patient_id_seq
                    START WITH 1
                    INCREMENT BY 1
                    MINVALUE 1;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        SELECT setval(
            'afasync_patient_id_seq',
            GREATEST(
                COALESCE(MAX(CAST(SUBSTRING(afya_id FROM 4) AS BIGINT)), 0),
                1
            ),
            COALESCE(MAX(CAST(SUBSTRING(afya_id FROM 4) AS BIGINT)), 0) > 0
        )
        FROM afya_identities
        """
    )


def downgrade() -> None:
    # Do not remove a sequence that may have existed before this repair.
    pass
