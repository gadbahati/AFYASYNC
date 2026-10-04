#!/usr/bin/env python3
"""Phase 148 — merge full App.tsx from historical SHA with clinical routes.

Run from repo root:
  python3 scripts/merge_app_routes.py
  git add frontend/src/App.tsx && git commit -m "Phase 148: full App routes" && git push

Developed by BAHATI GAD WANGWE.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "src" / "App.tsx"
GOOD_SHA = "b7e5a318802fa625a0fd780f978b43389df1f341"

EXTRA_IMPORTS = [
    'import { RadiologyPage } from "./pages/RadiologyPage";',
    'import { ClinicalWorklistPage } from "./pages/ClinicalWorklistPage";',
]

EXTRA_ROUTES = [
    '<Route path="/clinical-worklist" element={<ClinicalWorklistPage />} />',
    '<Route path="/radiology" element={<RadiologyPage />} />',
]


def main() -> None:
    raw = subprocess.check_output(
        ["git", "show", f"{GOOD_SHA}:frontend/src/App.tsx"],
        cwd=ROOT,
    ).decode()
    text = raw
    for line in EXTRA_IMPORTS:
        name = line.split("{")[1].split("}")[0].strip()
        if name not in text:
            anchor = 'import { EncountersPage } from "./pages/EncountersPage";'
            if anchor in text:
                text = text.replace(anchor, anchor + "\n" + line)
            else:
                text = line + "\n" + text
    for route in EXTRA_ROUTES:
        path = route.split('path="')[1].split('"')[0]
        if path not in text:
            needle = '<Route path="/encounters" element={<EncountersPage />} />'
            if needle in text:
                text = text.replace(needle, route + "\n        " + needle, 1)
            else:
                text = text.replace(
                    "</Routes>",
                    "  " + route + "\n        </Routes>",
                    1,
                )
    APP.write_text(text if text.endswith("\n") else text + "\n")
    print(f"Wrote {APP} ({len(text)} bytes) from {GOOD_SHA} + clinical routes")


if __name__ == "__main__":
    main()
