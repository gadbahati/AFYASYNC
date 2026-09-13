"""merge all remaining Alembic heads into one deployment path

Revision ID: 0051_merge_remaining_heads
Revises: 0015_national_facility_network_permissions, 0018_preauthorization_idempotency,
         0028_remove_duplicate_integration_reference_index, 0047_radiology_review,
         0050_encounter_coverage_mode
"""

revision = "0051_merge_remaining_heads"
down_revision = (
    "0015_national_facility_network_permissions",
    "0018_preauthorization_idempotency",
    "0028_remove_duplicate_integration_reference_index",
    "0047_radiology_review",
    "0050_encounter_coverage_mode",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Graph-only merge revision."""


def downgrade() -> None:
    """Graph-only merge revision."""
