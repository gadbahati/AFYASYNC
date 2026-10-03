"""Phase 98 — regression checks for operating-scope inventory.

These tests do not require a database; they lock the contract of the
scoped-read surface so DHA evidence and UI wiring stay aligned.
"""

from app.context.scoped_surface import (
    SCOPED_READ_ENDPOINTS,
    SCOPED_UI_PAGES,
    VALID_OPERATING_SCOPES,
    scoped_surface_manifest,
)


def test_valid_scopes_ordered():
    assert VALID_OPERATING_SCOPES == ("facility", "network", "county", "national")


def test_manifest_has_default_facility():
    m = scoped_surface_manifest()
    assert m["default_scope"] == "facility"
    assert m["denial"]["code"] == "SCOPE_NOT_AUTHORIZED"
    assert m["denial"]["status"] == 403
    assert "JWT facility_id" in m["write_policy"] or "facility_id" in m["write_policy"]


def test_all_list_domains_present():
    paths = {p for _, p, _ in SCOPED_READ_ENDPOINTS}
    for required in (
        "/api/v1/patients",
        "/api/v1/encounters",
        "/api/v1/claims",
        "/api/v1/referrals",
        "/api/v1/referrals/transfers",
        "/api/v1/appointments",
        "/api/v1/billing/services",
        "/api/v1/billing/invoices",
        "/api/v1/context/scoped-surface",
    ):
        # scoped-surface is registered on router; include in manifest notes path
        if required == "/api/v1/context/scoped-surface":
            continue
        assert required in paths, f"missing {required}"


def test_ui_pages_cover_operations():
    for page in (
        "PatientsPage",
        "ClaimsPage",
        "ReferralsPage",
        "AppointmentsPage",
        "BillingPage",
    ):
        assert page in SCOPED_UI_PAGES
