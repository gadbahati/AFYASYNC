from app.main import app


def _paths() -> set[str]:
    """Return every route path FastAPI actually exposes.

    Walking `app.routes` directly is not reliable across FastAPI versions:
    newer versions wrap included routers in `fastapi.routing._IncludedRouter`
    objects that don't expose `.path`. The OpenAPI schema is the
    version-stable source of truth for what's actually registered.
    """
    return set(app.openapi()["paths"].keys())


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
