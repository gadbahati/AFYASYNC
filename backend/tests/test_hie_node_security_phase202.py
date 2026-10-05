from pathlib import Path
P=Path(__file__).parents[1]/"app"/"hie"
service=(P/"service.py").read_text()
router=(P/"router.py").read_text()

def test_hie_node_upsert_is_facility_bound():
    assert "def upsert_node(db: Session, *, data: dict, facility_id: UUID)" in service
    assert 'HIE_NODE_ACCESS_DENIED' in service
    assert 'HIE_NODE_FACILITY_ACCESS_DENIED' in service
    assert 'row.facility_id = facility_id' in service

def test_hie_node_router_passes_authenticated_facility():
    assert 'upsert_node(db, data=body.model_dump(), facility_id=facility_id)' in router

def test_hie_node_listing_does_not_expose_endpoint():
    assert '"endpoint_url": n.endpoint_url' not in router
