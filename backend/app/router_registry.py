"""Phase 140 — load routers from routers.csv. Developed by BAHATI GAD WANGWE."""
from pathlib import Path

_CSV = Path(__file__).with_name("routers.csv")


def _load() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    if not _CSV.exists():
        return [
            ("app.clinical.router", "router", "clinical_router"),
            ("app.clinical.worklist_routes", "worklist_router", "worklist_router"),
            ("app.encounters.router", "router", "encounters_router"),
            ("app.auth", "router", "auth_router"),
        ]
    for line in _CSV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) != 3:
            continue
        rows.append((parts[0], parts[1], parts[2]))
    return rows


ROUTERS: list[tuple[str, str, str]] = _load()
