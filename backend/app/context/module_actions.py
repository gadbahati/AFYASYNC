"""Phase 99 — module actions: which UI routes a permission set may open.

Workspace visibility (Phase 89) is coarse. This catalog is finer:
path → required permission prefix(es). Backend remains the authority;
the UI only filters navigation, never grants access.

Developer: BAHATI GAD WANGWE
"""

from __future__ import annotations

# Longest-prefix match wins. Empty tuple = always allowed for authenticated staff.
PATH_PERMISSION_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("/", ()),
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
    ("/national", ("national.", "analytics.", "reports.")),
    ("/public-health", ("public_health.", "national.")),
    ("/security", ("security.", "privacy.")),
    ("/privacy", ("privacy.", "security.")),
    ("/certification", ("certification.",)),
    ("/risk", ("risk.",)),
    ("/change-control", ("change.",)),
    ("/production", ("production.", "observability.")),
    ("/offline", ("offline.", "continuity.")),
    ("/continuity", ("continuity.", "disaster.")),
    ("/disaster", ("disaster.", "continuity.")),
    ("/observability", ("observability.", "performance.")),
    ("/analytics", ("analytics.", "insight.")),
    ("/intelligence", ("analytics.", "insight.", "warehouse.")),
]


def _prefixes_for_path(path: str) -> tuple[str, ...]:
    path = (path or "/").split("?", 1)[0].rstrip("/") or "/"
    best: tuple[str, ...] | None = None
    best_len = -1
    for prefix, required in PATH_PERMISSION_RULES:
        rule = prefix.rstrip("/") or "/"
        if path == rule or path.startswith(rule + "/"):
            if len(rule) > best_len:
                best = required
                best_len = len(rule)
    return best if best is not None else ("*",)  # unknown path: deny unless admin


def path_allowed(path: str, permissions: list[str], *, is_admin: bool) -> bool:
    if is_admin:
        return True
    required = _prefixes_for_path(path)
    if not required:
        return True
    if required == ("*",):
        return False
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


def module_actions_payload(permissions: list[str], *, is_admin: bool) -> dict:
    return {
        "allowed_paths": allowed_paths_for(permissions, is_admin=is_admin),
        "policy": "Navigation filter only; API routes still enforce require_permission.",
        "is_admin": is_admin,
    }
