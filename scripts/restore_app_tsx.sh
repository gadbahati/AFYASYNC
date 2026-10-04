#!/bin/bash
# Phase 141 recovery: restore full App.tsx and ensure clinical worklist route
# Developed by BAHATI GAD WANGWE
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
GOOD_SHA="b7e5a318802fa625a0fd780f978b43389df1f341"
echo "Restoring frontend/src/App.tsx from $GOOD_SHA ..."
git show "${GOOD_SHA}:frontend/src/App.tsx" > frontend/src/App.tsx
if ! grep -q 'ClinicalWorklistPage' frontend/src/App.tsx; then
  python3 - <<'PY'
from pathlib import Path
p = Path("frontend/src/App.tsx")
t = p.read_text()
if 'ClinicalWorklistPage' not in t:
    t = t.replace(
        'import { EncountersPage } from "./pages/EncountersPage";',
        'import { EncountersPage } from "./pages/EncountersPage";\nimport { ClinicalWorklistPage } from "./pages/ClinicalWorklistPage";',
    )
if 'clinical-worklist' not in t:
    for a, b in [
        ('/><Route path="/encounters" element={<EncountersPage />} />',
         '/><Route path="/clinical-worklist" element={<ClinicalWorklistPage />} /><Route path="/encounters" element={<EncountersPage />} />'),
        ('<Route path="/encounters" element={<EncountersPage />} />',
         '<Route path="/clinical-worklist" element={<ClinicalWorklistPage />} />\n        <Route path="/encounters" element={<EncountersPage />} />'),
    ]:
        if a in t:
            t = t.replace(a, b, 1)
            break
p.write_text(t)
print("worklist route ensured")
PY
fi
echo "Done. Review: git diff frontend/src/App.tsx"
echo "Then: git add frontend/src/App.tsx && git commit -m 'restore full App.tsx with clinical-worklist' && git push"
