from app.main_application import _failed, _mounted


def test_all_registered_routers_mount_without_failure():
    assert _failed == [], f"Router mount failures: {_failed}"
    assert len(_mounted) >= 120
