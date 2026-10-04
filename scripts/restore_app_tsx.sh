#!/bin/bash
# Phase 140 recovery: restore full App.tsx and add clinical worklist route
# Developed by BAHATI GAD WANGWE
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
git show b7e5a318802fa625a0fd780f978b43389df1f341:frontend/src/App.tsx > frontend/src/App.tsx
if ! grep -q ClinicalWorklistPage frontend/src/App.tsx; then
  sed -i 's|import { EncountersPage } from "./pages/EncountersPage";|import { EncountersPage } from "./pages/EncountersPage";\nimport { ClinicalWorklistPage } from "./pages/ClinicalWorklistPage";|' frontend/src/App.tsx
fi
if ! grep -q clinical-worklist frontend/src/App.tsx; then
  sed -i 's|path="/encounters" element={<EncountersPage />}|path="/clinical-worklist" element={<ClinicalWorklistPage />} />\n        <Route path="/encounters" element={<EncountersPage />}|' frontend/src/App.tsx
fi
echo "App.tsx restored from b7e5a318 + worklist route. Review git diff and commit."
