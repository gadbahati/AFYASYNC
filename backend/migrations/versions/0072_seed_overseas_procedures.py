"""seed representative SHA Treat Abroad procedures

Revision ID: 0072_seed_overseas_procedures
Revises: 0071_beast_portal_consent_treat_abroad
"""

from alembic import op

revision = "0072_seed_overseas_procedures"
down_revision = "0071_beast_portal_consent_treat_abroad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO approved_overseas_procedures
          (id, code, name, description, justification, max_cover_kes, is_active)
        VALUES
          (gen_random_uuid(), 'OTA-LIVER-TX', 'Liver transplant',
           'Orthotopic liver transplantation',
           'Specialised transplant capacity and post-operative support not fully available in Kenya',
           500000, true),
          (gen_random_uuid(), 'OTA-BMT', 'Bone marrow transplant',
           'Allogeneic or autologous bone marrow / stem cell transplant',
           'Limited local capacity for complex haematopoietic stem cell transplantation',
           500000, true),
          (gen_random_uuid(), 'OTA-PED-CARDIAC', 'Complex paediatric cardiac surgery',
           'Complex congenital heart surgery in children',
           'Selected complex congenital procedures still require overseas specialist centres',
           500000, true),
          (gen_random_uuid(), 'OTA-JOINT-COMPLEX', 'Complex joint reconstruction / replacement',
           'Complex joint procedures not routinely available locally',
           'Specialised implants and expertise limited for selected complex reconstructions',
           500000, true),
          (gen_random_uuid(), 'OTA-NEURO-COMPLEX', 'Complex neurosurgical procedure',
           'Selected complex neurosurgical interventions',
           'Certain advanced neurosurgical procedures require overseas capacity',
           500000, true)
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM approved_overseas_procedures
        WHERE code IN (
          'OTA-LIVER-TX', 'OTA-BMT', 'OTA-PED-CARDIAC',
          'OTA-JOINT-COMPLEX', 'OTA-NEURO-COMPLEX'
        )
        """
    )
