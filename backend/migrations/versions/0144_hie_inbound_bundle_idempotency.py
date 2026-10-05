"""Enforce idempotent inbound HIE document identity.

A source node must not be able to create multiple inbound records for the
same FHIR Bundle id. NULL bundle IDs remain allowed for legacy/rejected
payloads that do not carry a Bundle id.
"""
from alembic import op
import sqlalchemy as sa


revision = "0144_hie_inbound_bundle_idempotency"
down_revision = "0143_hie_consent_purpose"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    duplicates = bind.execute(
        sa.text(
            """
            SELECT source_node_id, bundle_id, count(*) AS duplicate_count
            FROM hie_inbound_documents
            WHERE source_node_id IS NOT NULL
              AND bundle_id IS NOT NULL
            GROUP BY source_node_id, bundle_id
            HAVING count(*) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicates:
        raise RuntimeError(
            "HIE_INBOUND_DUPLICATE_BUNDLE_IDS_EXIST:"
            f"{duplicates.source_node_id}:{duplicates.bundle_id}"
        )

    op.create_index(
        "uq_hie_inbound_source_bundle",
        "hie_inbound_documents",
        ["source_node_id", "bundle_id"],
        unique=True,
        postgresql_where=sa.text("bundle_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_hie_inbound_source_bundle",
        table_name="hie_inbound_documents",
    )
