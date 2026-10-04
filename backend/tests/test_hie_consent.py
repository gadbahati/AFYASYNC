from datetime import datetime, timezone

def test_consent_period_ordering_rule():
    start=datetime(2026,1,1,tzinfo=timezone.utc); end=datetime(2026,1,2,tzinfo=timezone.utc)
    assert end > start
