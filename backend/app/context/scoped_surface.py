"""Canonical inventory of operating-scope-aware read surfaces.

Used for documentation, DHA evidence packs, and regression checks.
Writes remain bound to the JWT facility context only.

Developer: BAHATI GAD WANGWE
"""

from __future__ import annotations

VALID_OPERATING_SCOPES: tuple[str, ...] = ("facility", "network", "county", "national")

# (method, path, notes)
SCOPED_READ_ENDPOINTS: list[tuple[str, str, str]] = [
    ("GET", "/api/v1/context", "Overview includes scope summary"),
    ("GET", "/api/v1/context/scope-summary", "Facility counts for active scope"),
    ("GET", "/api/v1/context/operations-summary", "Aggregates filtered by resolve_facility_ids"),
    ("POST", "/api/v1/context/scope", "Records scope selection; audits denial"),
    ("GET", "/api/v1/patients", "List patients in scope"),
    ("GET", "/api/v1/patients/search", "Search patients in scope"),
    ("GET", "/api/v1/encounters", "List encounters in scope"),
    ("GET", "/api/v1/claims", "List claims in scope"),
    ("GET", "/api/v1/referrals", "Referrals where source/destination in scope"),
    ("GET", "/api/v1/referrals/transfers", "Transfers where source/destination in scope"),
    ("GET", "/api/v1/appointments", "Appointments in scope"),
    ("GET", "/api/v1/billing/services", "Active billing services in scope"),
    ("GET", "/api/v1/billing/invoices", "Invoices in scope"),
]

# UI routes that must pass WorkspaceContext.scope to the APIs above
SCOPED_UI_PAGES: tuple[str, ...] = (
    "PatientsPage",
    "EncountersPage",
    "ClaimsPage",
    "ReferralsPage",
    "AppointmentsPage",
    "BillingPage",
)


def scoped_surface_manifest() -> dict:
    return {
        "valid_scopes": list(VALID_OPERATING_SCOPES),
        "default_scope": "facility",
        "authorization": {
            "facility": "All authenticated facility staff",
            "network": "Staff with multi-facility assignments or system admin",
            "county": "System administrator only",
            "national": "System administrator only",
        },
        "denial": {
            "status": 403,
            "code": "SCOPE_NOT_AUTHORIZED",
            "audit_action": "SCOPE_NOT_AUTHORIZED",
        },
        "read_endpoints": [
            {"method": m, "path": p, "notes": n} for m, p, n in SCOPED_READ_ENDPOINTS
        ],
        "ui_pages": list(SCOPED_UI_PAGES),
        "write_policy": "All create/update/delete operations remain bound to JWT facility_id only.",
        "empty_scope_policy": "resolve_facility_ids never returns an empty list when authorized; falls back to token facility.",
    }
