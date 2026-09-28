"""universal financing identity resolution

Revision ID: 0098_universal_identity
Revises: 0097_multi_payer_eligibility
"""
from alembic import op

revision = "0098_universal_identity"
down_revision = "0097_multi_payer_eligibility"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_index("ix_financing_person_identifiers_type_hash","financing_person_identifiers",["identifier_type","identifier_hash"])
    op.create_index("ix_financing_person_identifiers_status","financing_person_identifiers",["status"])

def downgrade() -> None:
    op.drop_index("ix_financing_person_identifiers_status", table_name="financing_person_identifiers")
    op.drop_index("ix_financing_person_identifiers_type_hash", table_name="financing_person_identifiers")
