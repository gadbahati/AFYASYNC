from pathlib import Path


ROUTER = Path(__file__).parents[1] / "app" / "hie" / "router.py"


def test_mutating_hie_routes_require_write_permission():
    source = ROUTER.read_text()
    inbound_start = source.index('@router.post("/inbound")')
    inbound_end = source.index('@router.get("/inbound")', inbound_start)
    assert 'require_permission("patients.record.write")' in source[inbound_start:inbound_end]

    resolve_start = source.index('@router.post("/inbound/{inbound_id}/resolve")')
    resolve_end = source.index('@router.put("/nodes")', resolve_start)
    assert 'require_permission("patients.record.write")' in source[resolve_start:resolve_end]

    node_start = source.index('@router.put("/nodes")')
    node_end = source.index('@router.get("/nodes")', node_start)
    assert 'require_permission("patients.record.write")' in source[node_start:node_end]
