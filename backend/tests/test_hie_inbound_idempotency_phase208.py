from pathlib import Path

SERVICE = Path(__file__).parents[1] / "app" / "hie" / "service.py"
ROUTER = Path(__file__).parents[1] / "app" / "hie" / "router.py"
MODEL = Path(__file__).parents[1] / "app" / "hie" / "models.py"
MIGRATION = Path(__file__).parents[1] / "migrations" / "versions" / "0144_hie_inbound_bundle_idempotency.py"


def test_phase208_uses_source_node_and_bundle_id_as_inbound_message_identity():
    source = SERVICE.read_text()
    assert 'HieInboundDocument.source_node_id == source_node_id' in source
    assert 'HieInboundDocument.bundle_id == bundle_id' in source
    assert '"idempotent_replay": True' in source


def test_phase208_database_constraint_prevents_duplicate_inbound_bundles():
    model = MODEL.read_text()
    migration = MIGRATION.read_text()
    assert "UniqueConstraint" in model
    assert '"source_node_id",' in model
    assert '"bundle_id",' in model
    assert 'name="uq_hie_inbound_source_bundle"' in model
    assert 'unique=True' in migration
    assert 'bundle_id IS NOT NULL' in migration


def test_phase208_concurrent_unique_conflict_returns_idempotent_replay():
    router = ROUTER.read_text()
    assert "IntegrityError" in router
    assert "HIE_INBOUND_IDEMPOTENCY_CONFLICT" in router
    assert "idempotent_replay" in router
    assert "db.rollback()" in router


def test_phase208_replay_does_not_run_mpi_again():
    router = ROUTER.read_text()
    marker = 'if result["validation_status"] == "ACCEPTED" and not result.get("idempotent_replay"):'
    assert marker in router
    assert "resolve_inbound_patient(" in router


def test_phase208_migration_is_chained_from_phase207_schema_head():
    migration = MIGRATION.read_text()
    assert 'revision = "0144_hie_inbound_bundle_idempotency"' in migration
    assert 'down_revision = "0143_hie_consent_purpose"' in migration
