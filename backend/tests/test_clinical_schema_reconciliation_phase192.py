"""Phase 192/0142 regression tests for clinical schema alignment."""
from app.clinical.models import Allergy, CarePlan, ClinicalNote, Consultation, Diagnosis, Procedure, TriageAssessment, Vital


def test_clinical_models_match_persisted_runtime_columns():
    assert {"doctor_id", "clinical_notes", "treatment_plan", "status", "signed_by"} <= set(Consultation.__table__.columns.keys())
    assert {"systolic_bp", "diastolic_bp", "oxygen_saturation", "height_cm", "bmi"} <= set(Vital.__table__.columns.keys())
    assert {"diagnosis_code", "diagnosis_name", "status", "created_at"} <= set(Diagnosis.__table__.columns.keys())
    assert {"procedure_code", "procedure_name", "procedure_type", "status", "outcome"} <= set(Procedure.__table__.columns.keys())
    assert {"content", "status", "signed_at", "signed_by", "updated_at"} <= set(ClinicalNote.__table__.columns.keys())
    assert {"facility_id", "clinical_notes", "target_date", "completed_at"} <= set(CarePlan.__table__.columns.keys())
    assert {"facility_id", "allergen", "onset_date", "notes"} <= set(Allergy.__table__.columns.keys())
    assert {"assessed_by", "vital_id", "acuity", "priority", "red_flags"} <= set(TriageAssessment.__table__.columns.keys())
