import { Navigate, Outlet, useLocation } from "react-router-dom";
import { getAccessToken } from "../auth/storage";
import { useAuth } from "../auth/AuthContext";

export function GovernmentProtectedRoute() {
  const auth = useAuth();
  const location = useLocation();
  if (!auth.ready) return <div className="auth-page"><div className="card auth-card"><p className="muted">Checking your secure session…</p></div></div>;
  if (!getAccessToken() || !auth.username || auth.portalType !== "government") return <Navigate to="/login/government" replace state={{from: location.pathname}} />;
  if (!auth.organizationId) return <Navigate to="/login/government" replace />;
  return <Outlet />;
}
