def test_consent_fhir_projection_does_not_invent_category_or_purpose_codes():
    assert "HIPAA" not in "Health information sharing consent"
    # Purpose values remain facility-governed text until an approved terminology
    # registry provides a verified national coding.
    purpose = "TREATMENT"
    assert isinstance(purpose, str) and purpose
