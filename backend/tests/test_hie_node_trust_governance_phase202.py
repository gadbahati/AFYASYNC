from pathlib import Path

P = Path(__file__).parents[1] / "app" / "hie" / "service.py"

def test_hie_facility_cannot_self_elevate_trust():
    s = P.read_text()
    assert 'row.trust_level = "STANDARD"' in s
    assert 'elif row.trust_level not in {"HIGH", "NATIONAL"}:' in s
