"""Harden production patient registration prerequisites.

Revision ID: 0060_patient_registration_runtime_safety
Revises: 0059_repair_patient_identity_sequence
"""

from alembic import op

revision = "0060_patient_registration_runtime_safety"
down_revision = "0059_repair_patient_identity_sequence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure the runtime dependency exists even on databases upgraded from a
    # partially applied historical migration set.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_class
                WHERE relkind = 'S' AND relname = 'afasync_patient_id_seq'
            ) THEN
                CREATE SEQUENCE afasync_patient_id_seq
                    START WITH 1 INCREMENT BY 1 MINVALUE 1;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        DECLARE
            highest BIGINT;
        BEGIN
            SELECT COALESCE(
                MAX((substring(afya_id FROM 4))::BIGINT)
                FILTER (WHERE afya_id ~ '^AF-[0-9]+$'),
                0
            ) INTO highest
            FROM afya_identities;

            IF highest > 0 THEN
                PERFORM setval('afasync_patient_id_seq', highest, true);
            ELSE
                PERFORM setval('afasync_patient_id_seq', 1, false);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    pass
