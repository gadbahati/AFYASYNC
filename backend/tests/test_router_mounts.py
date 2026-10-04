from app.main_application import _failed, _mounted


def test_all_registered_routers_mount_without_failure():
    assert _failed == [], f"Router mount failures: {_failed}"
    assert len(_mounted) >= 120


def test_registered_http_routes_are_not_duplicated():
    from app.main_application import app

    seen = {}
    duplicates = []
    for route in app.routes:
        methods = getattr(route, "methods", set()) or set()
        path = getattr(route, "path", "")
        for method in methods:
            key = (method.upper(), path)
            if key in seen:
                duplicates.append(key)
            else:
                seen[key] = getattr(route, "name", "")
    assert duplicates == [], f"Duplicate HTTP routes: {duplicates}"
