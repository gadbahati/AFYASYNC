import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import "./app-shell.css";
import "./national-brand.css";
import "./institutional-brand.css";
import "./dashboard.css";
import "./portal.css";
/* Must load last — overrides conflicting shell/brand rules */
import "./layout-fix.css";

import { api, request } from "./api/client";
import { bindClinicalExtras } from "./api/clinicalExtras";

// Phase 138 — align clinical client paths (timeline, notes, close, summary)
bindClinicalExtras(api, request);

if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* offline shell optional */
    });
  });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
