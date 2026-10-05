from pathlib import Path

SERVICE = Path(__file__).parents[1] / "app" / "hie" / "service.py"
ROUTER = Path(__file__).parents[1] / "app" / "hie" / "router.py"

def test_hie_node_upsert_requires_facility_context():
    source = SERVICE.read_text()
    assert "def upsert_node(db: Session, *, data: dict, facility_id: UUID)" in source
    assert 'HIE_NODE_ACCESS_DENIED' in source
    assert 'HIE_NODE_FACILITY_ACCESS_DENIED' in source

def test_hie_node_route_passes_facility_context():
    source = ROUTER.read_text()
    assert 'upsert_node(db, data=body.model_dump(), facility_id=facility_id)' in source
