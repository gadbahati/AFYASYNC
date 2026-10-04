"""Phase 141 — load routers from CSV parts. Developed by BAHATI GAD WANGWE."""
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_FILES = ("routers.csv", "routers_1.csv", "routers_2.csv", "routers_more.csv")


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
    rows: list[tuple[str, str, str]] = []
    for name in _FILES:
        rows.extend(_load_csv(name))
    if not rows:
        return [
            ("app.clinical.router", "router", "clinical_router"),
            ("app.clinical.worklist_routes", "worklist_router", "worklist_router"),
            ("app.encounters.router", "router", "encounters_router"),
            ("app.auth", "router", "auth_router"),
        ]
    seen: set[str] = set()
    out: list[tuple[str, str, str]] = []
    for mod, attr, alias in rows:
        if alias in seen:
            continue
        seen.add(alias)
        out.append((mod, attr, alias))
    return out


ROUTERS: list[tuple[str, str, str]] = _load()
