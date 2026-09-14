import { Navigate, Outlet, useLocation } from "react-router-dom";
import { getAccessToken } from "../auth/storage";
import { useAuth } from "../auth/AuthContext";

export function ProtectedRoute() {
  const auth = useAuth();
  const location = useLocation();

  if (!auth.ready) {
    return <div className="auth-page"><div className="card auth-card"><p className="muted">Checking your secure session…</p></div></div>;
  }

  if (!getAccessToken() || !auth.username) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (!auth.facilityId && !auth.pendingFacilities) {
    return <Navigate to="/select-facility" replace />;
  }

  return <Outlet />;
}
