from pathlib import Path


ROUTER = Path(__file__).parents[1] / "app" / "hie" / "router.py"


def test_hie_package_and_communication_generation_require_write_permission():
    source = ROUTER.read_text()
    start = source.index('@router.post("/referral-package")')
    end = source.index('@router.post("/inbound")', start)
    assert 'require_permission("patients.record.write")' in source[start:end]

    start = source.index('@router.get("/referrals/{referral_id}/communication")')
    end = source.index('@router.get("/lab-results', start)
    assert 'require_permission("patients.record.write")' in source[start:end]
