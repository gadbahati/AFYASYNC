"""Phase 138 — clinical API path contract.

Canonical paths and accepted aliases so frontend and backend stay aligned.

Developed by BAHATI GAD WANGWE.
"""

CLINICAL_PATH_CONTRACT = {
    "timeline": {
        "canonical": "/api/v1/encounters/{id}/clinical-timeline",
        "aliases": ["/api/v1/encounters/{id}/clinical"],
    },
    "notes": {
        "canonical": "/api/v1/encounters/{id}/notes",
        "aliases": ["/api/v1/encounters/{id}/clinical-notes"],
    },
    "summary": {"canonical": "/api/v1/encounters/{id}/summary", "aliases": []},
    "discharge": {"canonical": "/api/v1/encounters/{id}/discharge", "aliases": []},
    "orders": {"canonical": "/api/v1/encounters/{id}/orders", "aliases": []},
    "close": {"canonical": "/api/v1/encounters/{id}/close", "aliases": []},
}


def assert_department_services_loaded() -> dict:
    """Fail fast if lab/pharmacy service modules were wiped (empty files)."""
    import importlib
    import inspect

    report = {}
    for mod_name, required in [
        ("app.laboratory.service", ["create_order", "enter_result", "verify_result"]),
        ("app.pharmacy.service", ["PharmacyError", "dispense_prescription"]),
    ]:
        mod = importlib.import_module(mod_name)
        source = inspect.getsource(mod)
        if len(source.strip()) < 50:
            raise RuntimeError(f"EMPTY_SERVICE_MODULE:{mod_name}")
        missing = [n for n in required if not hasattr(mod, n)]
        if missing:
            raise RuntimeError(f"INCOMPLETE_SERVICE_MODULE:{mod_name}:{','.join(missing)}")
        report[mod_name] = "ok"
    return report
