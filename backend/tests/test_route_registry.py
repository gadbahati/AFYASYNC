from app.main import app


def _paths() -> set[str]:
    return {getattr(route, "path", "") for route in app.routes}


def test_system_routes_registered() -> None:
    paths = _paths()
    assert "/health" in paths
    assert "/ready" in paths
    assert "/api/v1" in paths


def test_core_module_routes_registered() -> None:
    paths = _paths()
    expected = {
        "/api/v1/auth/login",
        "/api/v1/patients",
        "/api/v1/encounters",
        "/api/v1/encounters/{encounter_id}/clinical",
        "/api/v1/referrals",
        "/api/v1/referrals/transfers",
        "/api/v1/portal/me",
        "/api/v1/portal/encounters",
        "/api/v1/notifications",
        "/api/v1/billing/charges",
        "/api/v1/coverage",
    }
    missing = expected - paths
    assert not missing, f"Missing routes: {sorted(missing)}"
