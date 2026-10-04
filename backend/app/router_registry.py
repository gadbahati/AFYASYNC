"""Phase 140 — load routers from CSV parts. Developed by BAHATI GAD WANGWE."""
from pathlib import Path

_DIR = Path(__file__).resolve().parent


def _load_csv(name: str) -> list[tuple[str, str, str]]:
    path = _DIR / name
    rows: list[tuple[str, str, str]] = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) != 3:
            continue
        rows.append((parts[0], parts[1], parts[2]))
    return rows


def _load() -> list[tuple[str, str, str]]:
    rows = _load_csv("routers.csv") + _load_csv("routers_more.csv")
    if not rows:
        return [
            ("app.clinical.router", "router", "clinical_router"),
            ("app.clinical.worklist_routes", "worklist_router", "worklist_router"),
            ("app.encounters.router", "router", "encounters_router"),
            ("app.auth", "router", "auth_router"),
            ("app.laboratory.router", "router", "laboratory_router"),
            ("app.pharmacy.router", "router", "pharmacy_router"),
            ("app.radiology.router", "router", "radiology_router"),
            ("app.billing.router", "router", "billing_router"),
            ("app.claims.router", "router", "claims_router"),
            ("app.patients.router", "router", "patients_router"),
            ("app.appointments.router", "router", "appointments_router"),
            ("app.government.router", "router", "government_router"),
        ]
    # de-dupe by alias
    seen: set[str] = set()
    out: list[tuple[str, str, str]] = []
    for mod, attr, alias in rows:
        if alias in seen:
            continue
        seen.add(alias)
        out.append((mod, attr, alias))
    return out


ROUTERS: list[tuple[str, str, str]] = _load()
