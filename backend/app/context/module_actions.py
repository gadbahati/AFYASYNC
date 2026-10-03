"""Phase 99/100 — module actions: which UI routes a permission set may open.

Workspace visibility (Phase 89) is coarse. This catalog is finer:
path → required permission prefix(es). Backend remains the authority;
the UI only filters navigation, never grants access.

Uncatalogued paths are not auto-denied (API still enforces require_permission).
Catalogued paths are denied unless the caller has a matching permission.

Developer: BAHATI GAD WANGWE
"""

from __future__ import annotations

# Longest-prefix match wins. Empty tuple = always allowed for authenticated staff.
PATH_PERMISSION_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("/", ()),
    ("/workspace", ()),
    ("/appointments", ("appointments.",)),
    ("/queue", ("queue.", "appointments.")),
    ("/encounters", ("encounters.", "clinical.")),
    ("/laboratory", ("laboratory.", "lab.")),
    ("/pharmacy", ("pharmacy.",)),
    ("/mch", ("mch.", "clinical.", "encounters.")),
    ("/billing", ("billing.",)),
    ("/reports", ("reports.", "analytics.")),
    ("/patients/new", ("patients.write", "patients.create", "patients.")),
    ("/patients", ("patients.",)),
    ("/household-wallet", ("patients.", "coverage.", "portal.")),
    ("/messages", ("messages.", "portal.")),
    ("/referrals", ("referrals.",)),
    ("/care-coordination", ("care.", "referrals.", "patients.")),
    ("/interoperability", ("interoperability.", "hie.")),
    ("/health-exchange", ("interoperability.", "hie.")),
    ("/universal-identity", ("identity.",)),
    ("/national-identity", ("identity.", "national.")),
    ("/national-command-centre", ("national.", "analytics.")),
    ("/national-intelligence", ("national.", "analytics.")),
    ("/national-facilities", ("national.",)),
    ("/national-staff", ("national.", "staff.")),
    ("/national-payers", ("national.", "payer.")),
    ("/national-benefits", ("national.", "coverage.")),
    ("/national-supply", ("national.", "pharmacy.")),
    ("/national", ("national.", "analytics.", "reports.")),
    ("/referral-routing", ("referrals.", "interoperability.")),
    ("/referral-booking", ("referrals.", "appointments.")),
    ("/claims", ("claims.",)),
    ("/claims-clearinghouse", ("claims.",)),
    ("/coverage", ("coverage.",)),
    ("/financial-command-centre", ("revenue.", "claims.", "billing.")),
    ("/payer-command", ("payer.", "claims.")),
    ("/revenue-control-tower", ("revenue.",)),
    ("/revenue-cash-assurance", ("revenue.", "billing.")),
    ("/collection-work", ("revenue.", "billing.")),
    ("/revenue-recovery", ("revenue.",)),
    ("/denial-appeals", ("claims.", "revenue.")),
    ("/contract-guardrails", ("contract.",)),
    ("/contract-execution", ("contract.",)),
    ("/public-health", ("public_health.", "national.")),
    ("/security", ("security.", "privacy.")),
    ("/security-operations", ("security.", "privacy.")),
    ("/privacy", ("privacy.", "security.")),
    ("/certification", ("certification.",)),
    ("/risk", ("risk.",)),
    ("/risk-register", ("risk.",)),
    ("/change-control", ("change.",)),
    ("/production", ("production.", "observability.")),
    ("/offline", ("offline.", "continuity.")),
    ("/offline-clinic", ("offline.", "continuity.")),
    ("/continuity", ("continuity.", "disaster.")),
    ("/disaster", ("disaster.", "continuity.")),
    ("/disaster-recovery", ("disaster.", "continuity.")),
    ("/observability", ("observability.", "performance.")),
    ("/analytics", ("analytics.", "insight.")),
    ("/intelligence", ("analytics.", "insight.", "warehouse.")),
]


def _prefixes_for_path(path: str) -> tuple[str, ...] | None:
    """Return required prefixes, or None if path is not in the governance catalog."""
    path = (path or "/").split("?", 1)[0].rstrip("/") or "/"
    best: tuple[str, ...] | None = None
    best_len = -1
    for prefix, required in PATH_PERMISSION_RULES:
        rule = prefix.rstrip("/") or "/"
        if path == rule or path.startswith(rule + "/"):
            if len(rule) > best_len:
                best = required
                best_len = len(rule)
    return best


def path_allowed(path: str, permissions: list[str], *, is_admin: bool) -> bool:
    if is_admin:
        return True
    required = _prefixes_for_path(path)
    if required is None:
        # Uncatalogued route: do not block navigation (API still enforces).
        return True
    if not required:
        return True
    codes = set(permissions)
    for req in required:
        if req.endswith("."):
            if any(c.startswith(req) or c == req[:-1] for c in codes):
                return True
        elif req in codes or any(c.startswith(req + ".") for c in codes):
            return True
    return False


def allowed_paths_for(permissions: list[str], *, is_admin: bool) -> list[str]:
    """Distinct path prefixes the user may navigate to under module rules."""
    if is_admin:
        return sorted({p for p, _ in PATH_PERMISSION_RULES})
    out: list[str] = []
    for path, _ in PATH_PERMISSION_RULES:
        if path_allowed(path, permissions, is_admin=False):
            out.append(path)
    return out


def catalog_paths() -> list[str]:
    return sorted({p for p, _ in PATH_PERMISSION_RULES if p not in {"/"}})


def module_actions_payload(permissions: list[str], *, is_admin: bool) -> dict:
    return {
        "allowed_paths": allowed_paths_for(permissions, is_admin=is_admin),
        "catalog_paths": catalog_paths(),
        "policy": (
            "Catalogued paths require matching permissions. "
            "Uncatalogued paths are not blocked by the UI guard; API still uses require_permission."
        ),
        "is_admin": is_admin,
    }
