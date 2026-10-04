from datetime import timedelta
from app.hie.delivery_service import _backoff

def test_hie_delivery_backoff_is_bounded_and_exponential():
    assert _backoff(1) == timedelta(seconds=30)
    assert _backoff(2) == timedelta(seconds=60)
    assert _backoff(3) == timedelta(seconds=120)
    assert _backoff(10) == timedelta(seconds=3600)
