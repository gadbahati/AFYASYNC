import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const AUTH_BYPASS = import.meta.env.VITE_DISABLE_AUTH === "true";

export function ProtectedRoute({ requireFacility = true }: { requireFacility?: boolean }) {
  const auth = useAuth();

  if (AUTH_BYPASS) return <Outlet />;

  if (!auth.ready) {
    return <div className="page-center">Loading session…</div>;
  }

  if (!auth.username && !auth.pendingFacilities) {
    return <Navigate to="/login" replace />;
  }

  if (auth.pendingFacilities) {
    return <Navigate to="/select-facility" replace />;
  }

  if (requireFacility && !auth.facilityId) {
    return <Navigate to="/select-facility" replace />;
  }

  return <Outlet />;
}
