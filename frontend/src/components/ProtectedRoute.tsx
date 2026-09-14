import { Navigate, Outlet, useLocation } from "react-router-dom";
import { getAccessToken } from "../auth/storage";
import { useAuth } from "../auth/AuthContext";

export function ProtectedRoute() {
  const auth = useAuth();
  const location = useLocation();

  if (!auth.ready) {
    return <div className="auth-page"><div className="card auth-card"><p className="muted">Checking your secure session…</p></div></div>;
  }

  // Never mount protected pages without a real access token and authenticated user.
  if (!getAccessToken() || !auth.username) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  // A login that requires facility selection has a token, but that token is not
  // yet scoped to a facility. Do not mount any facility-protected page until the
  // user explicitly selects one.
  if (auth.pendingFacilities) {
    return <Navigate to="/select-facility" replace state={{ from: location.pathname }} />;
  }

  if (!auth.facilityId) {
    return <Navigate to="/select-facility" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
