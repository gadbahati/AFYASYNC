import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function ProtectedRoute({ requireFacility = true }: { requireFacility?: boolean }) {
  const auth = useAuth();

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
