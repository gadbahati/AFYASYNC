import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { FacilityOption } from "../api/types";
import { useAuth } from "../auth/AuthContext";

export function FacilitySelectPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [facilities, setFacilities] = useState<FacilityOption[]>(auth.pendingFacilities || []);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!auth.pendingFacilities);

  useEffect(() => {
    if (auth.pendingFacilities) return;
    let cancelled = false;
    api
      .facilities()
      .then((rows) => {
        if (!cancelled) setFacilities(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.code : "LOAD_FAILED");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [auth.pendingFacilities]);

  if (auth.ready && !auth.username && !auth.pendingFacilities) {
    return <Navigate to="/login" replace />;
  }

  if (auth.facilityId && !auth.pendingFacilities) {
    return <Navigate to="/" replace />;
  }

  async function choose(facility: FacilityOption) {
    setError(null);
    try {
      await auth.selectFacility(facility);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "FACILITY_SELECT_FAILED");
    }
  }

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h1>Select facility</h1>
        <p className="muted">Your account is active at more than one facility. Choose where you are working now.</p>
        {loading && <p>Loading facilities…</p>}
        {error && <div className="error">{error}</div>}
        <ul className="facility-list">
          {facilities.map((f) => (
            <li key={f.facility_id}>
              <button type="button" onClick={() => void choose(f)}>{f.facility_name}</button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
