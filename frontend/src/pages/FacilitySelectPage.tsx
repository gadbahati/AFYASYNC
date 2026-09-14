import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { getAccessToken } from "../auth/storage";
import type { FacilityOption } from "../api/types";
import { useAuth } from "../auth/AuthContext";

export function FacilitySelectPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [facilities, setFacilities] = useState<FacilityOption[]>(auth.pendingFacilities || []);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!auth.ready || auth.pendingFacilities || !auth.username || !getAccessToken()) return;
    let cancelled = false;
    setLoading(true);
    api
      .facilities()
      .then((rows) => {
        if (!cancelled) setFacilities(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message || err.code : "Unable to load facilities.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [auth.ready, auth.pendingFacilities, auth.username]);

  if (!auth.ready) {
    return <div className="auth-page"><div className="card auth-card"><p className="muted">Preparing facility selection…</p></div></div>;
  }
  if (!auth.username || !getAccessToken()) return <Navigate to="/login" replace />;
  if (auth.facilityId && !auth.pendingFacilities) return <Navigate to="/" replace />;

  async function choose(facility: FacilityOption) {
    setError(null);
    try {
      await auth.selectFacility(facility);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Unable to select facility.");
    }
  }

  return (
    <main className="auth-page" aria-label="Select facility">
      <div className="card auth-card">
        <div className="auth-brand"><div><div className="brand-kicker">AfyaSync workspace</div><h1>Select facility</h1></div></div>
        <p className="muted">Your staff account has access to more than one facility. Select the facility where you are working now.</p>
        {loading && <p className="muted">Loading facilities…</p>}
        {error && <div className="error" role="alert">{error}</div>}
        <ul className="facility-list">
          {facilities.map((facility) => (
            <li key={facility.facility_id}>
              <button type="button" onClick={() => void choose(facility)}>{facility.facility_name}</button>
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}
