"""merge laboratory catalog and patient identity migration heads

Revision ID: 0033_merge_lab_and_patient_identity
Revises: 0031_laboratory_test_catalog, 0032_patient_identity_id
"""

revision = "0033_merge_lab_and_patient_identity"
down_revision = ("0031_laboratory_test_catalog", "0032_patient_identity_id")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
