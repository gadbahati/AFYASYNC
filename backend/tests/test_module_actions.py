"""Phase 99 — module action path authorization unit tests."""

from app.context.module_actions import path_allowed, allowed_paths_for, module_actions_payload


def test_admin_sees_all_core_paths():
    paths = allowed_paths_for([], is_admin=True)
    assert "/patients" in paths
    assert "/claims" in paths
    assert "/appointments" in paths


def test_patient_read_allows_register_list():
    perms = ["patients.read"]
    assert path_allowed("/patients", perms, is_admin=False)
    assert path_allowed("/patients/abc", perms, is_admin=False)


def test_claims_without_perm_denied():
    assert not path_allowed("/claims", ["patients.read"], is_admin=False)


def test_dashboard_always_for_staff():
    assert path_allowed("/", ["appointments.read"], is_admin=False)


def test_payload_shape():
    p = module_actions_payload(["billing.read"], is_admin=False)
    assert "allowed_paths" in p
    assert "/billing" in p["allowed_paths"]
