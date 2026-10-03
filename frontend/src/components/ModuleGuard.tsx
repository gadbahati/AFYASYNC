import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import { useModuleAccess } from "../auth/ModuleAccessContext";

/** Phase 100 — block deep links to modules outside the caller's allowed_paths. */
export function ModuleGuard() {
  const location = useLocation();
  const access = useModuleAccess();

  if (!access.ready) {
    return (
      <div className="auth-page">
        <div className="card auth-card">
          <p className="muted">Loading your authorized modules…</p>
        </div>
      </div>
    );
  }

  if (!access.isAllowed(location.pathname)) {
    return (
      <section className="page-stack" style={{ maxWidth: 560, margin: "40px auto" }}>
        <article className="card">
          <p className="eyebrow">Access control</p>
          <h1>Module not authorized</h1>
          <p className="muted">
            Your role does not include permission to open <strong>{location.pathname}</strong>.
            This is enforced from your backend authorization profile, not only the menu.
          </p>
          <div className="form-actions" style={{ marginTop: 16 }}>
            <Link className="button" to="/workspace">
              Back to workspace
            </Link>
            <Link className="button secondary" to="/">
              Dashboard
            </Link>
          </div>
          <p className="muted small" style={{ marginTop: 12 }}>
            Developed by BAHATI GAD WANGWE · AfyaSync
          </p>
        </article>
        {/* Keep URL visible for support; do not auto-redirect so the denial is explicit. */}
      </section>
    );
  }

  return <Outlet />;
}

/** Optional hard redirect variant for routes that must never linger. */
export function ModuleGuardRedirect() {
  const location = useLocation();
  const access = useModuleAccess();
  if (!access.ready) return null;
  if (!access.isAllowed(location.pathname)) {
    return <Navigate to="/workspace" replace state={{ denied: location.pathname }} />;
  }
  return <Outlet />;
}
