from pathlib import Path


MIGRATION = Path(__file__).parents[1] / "migrations" / "versions" / "0143_hie_consent_purpose.py"
MODEL = Path(__file__).parents[1] / "app" / "hie" / "consent_models.py"


def test_hie_consent_purpose_migration_normalizes_legacy_typo():
    source = MIGRATION.read_text()
    assert "HOPERAT" in source
    assert "OPERATIONS" in source
    assert "UPDATE hie_consents" in source
    assert "server_default=sa.text("'OPERATIONS'")" in source


def test_hie_consent_model_defaults_to_operations():
    source = MODEL.read_text()
    assert 'default="OPERATIONS"' in source
