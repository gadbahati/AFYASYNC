"""beast mode: consent, portal booking/messaging, treat abroad, patient reset

Revision ID: 0071_beast_portal_consent_treat_abroad
Revises: 0070_allergy_permissions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0071_beast_portal_consent_treat_abroad"
down_revision = "0070_allergy_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Patient password reset ---
    op.create_table(
        "patient_password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(128), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("destination", sa.String(320), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_patient_password_reset_tokens_user_id", "patient_password_reset_tokens", ["user_id"])

    # --- Sensitive disease consent ---
    op.create_table(
        "sensitive_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sensitive_categories_code", "sensitive_categories", ["code"], unique=True)

    op.create_table(
        "sensitive_disease_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("diagnosis_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("diagnoses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("consent_given", sa.Boolean(), nullable=False),
        sa.Column("share_scope", sa.String(30), nullable=False, server_default="FACILITY_ONLY"),
        sa.Column("sensitive_category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sensitive_categories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("signature_data", sa.Text(), nullable=True),
        sa.Column("signature_method", sa.String(50), nullable=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("device_id", sa.String(150), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sensitive_consent_patient_diagnosis", "sensitive_disease_consents", ["patient_id", "diagnosis_id"])
    op.create_index("ix_sensitive_consent_facility", "sensitive_disease_consents", ["facility_id"])
    op.create_index("ix_sensitive_consent_share", "sensitive_disease_consents", ["consent_given", "patient_id"])
    op.create_index("ix_sensitive_disease_consents_diagnosis_id", "sensitive_disease_consents", ["diagnosis_id"], unique=True)

    # --- Treat Abroad ---
    op.create_table(
        "approved_overseas_procedures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("max_cover_kes", sa.Numeric(12, 2), nullable=False, server_default="500000"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_approved_overseas_procedures_code", "approved_overseas_procedures", ["code"], unique=True)

    op.create_table(
        "overseas_treatment_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_number", sa.String(40), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("procedure_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("approved_overseas_procedures.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("clinical_summary", sa.Text(), nullable=False),
        sa.Column("local_unavailability_reason", sa.Text(), nullable=False),
        sa.Column("referring_clinician_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="DRAFT"),
        sa.Column("sha_preauth_reference", sa.String(100), nullable=True),
        sa.Column("sha_commitment_letter_ref", sa.String(100), nullable=True),
        sa.Column("approved_amount_kes", sa.Numeric(12, 2), nullable=True),
        sa.Column("sha_decision_notes", sa.Text(), nullable=True),
        sa.Column("sha_decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("foreign_hospital_name", sa.String(300), nullable=True),
        sa.Column("foreign_hospital_country", sa.String(100), nullable=True),
        sa.Column("foreign_hospital_city", sa.String(100), nullable=True),
        sa.Column("planned_departure_date", sa.Date(), nullable=True),
        sa.Column("actual_departure_date", sa.Date(), nullable=True),
        sa.Column("treatment_start_date", sa.Date(), nullable=True),
        sa.Column("treatment_end_date", sa.Date(), nullable=True),
        sa.Column("return_date", sa.Date(), nullable=True),
        sa.Column("follow_up_facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("follow_up_notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_overseas_treatment_cases_case_number", "overseas_treatment_cases", ["case_number"], unique=True)
    op.create_index("ix_overseas_case_patient", "overseas_treatment_cases", ["patient_id"])
    op.create_index("ix_overseas_case_facility", "overseas_treatment_cases", ["facility_id"])
    op.create_index("ix_overseas_case_status", "overseas_treatment_cases", ["status"])

    # --- Portal appointment requests & messages ---
    op.create_table(
        "appointment_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("preferred_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("patient_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="PENDING"),
        sa.Column("facility_response_notes", sa.Text(), nullable=True),
        sa.Column("offered_appointment_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_appt_req_patient", "appointment_requests", ["patient_id"])
    op.create_index("ix_appt_req_facility_status", "appointment_requests", ["facility_id", "status"])

    op.create_table(
        "facility_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("sender_type", sa.String(20), nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("related_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appointment_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_facility_msg_thread", "facility_messages", ["patient_id", "facility_id", "created_at"])
    op.create_index("ix_facility_msg_facility_unread", "facility_messages", ["facility_id", "sender_type", "read_at"])

    # Seed default sensitive categories (idempotent by unique code)
    op.execute(
        """
        INSERT INTO sensitive_categories (id, code, name, description, is_active)
        VALUES
          (gen_random_uuid(), 'HIV', 'HIV / AIDS related', 'HIV and AIDS related diagnoses', true),
          (gen_random_uuid(), 'MENTAL_HEALTH', 'Mental health', 'Mental health conditions', true),
          (gen_random_uuid(), 'STI', 'Sexually transmitted infections', 'STI related diagnoses', true),
          (gen_random_uuid(), 'GBV', 'Gender-based violence related', 'GBV related findings', true),
          (gen_random_uuid(), 'SUBSTANCE', 'Substance use disorders', 'Substance use related diagnoses', true)
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("facility_messages")
    op.drop_table("appointment_requests")
    op.drop_table("overseas_treatment_cases")
    op.drop_table("approved_overseas_procedures")
    op.drop_table("sensitive_disease_consents")
    op.drop_table("sensitive_categories")
    op.drop_table("patient_password_reset_tokens")
