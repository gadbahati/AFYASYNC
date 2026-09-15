import { useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { getAccessToken } from "../auth/storage";
import type { FacilityOption } from "../api/types";
import { useAuth } from "../auth/AuthContext";

export function FacilitySelectPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [facilities, setFacilities] = useState<FacilityOption[]>(auth.pendingFacilities || []);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.ready || !auth.username || !getAccessToken()) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
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
  }, [auth.ready, auth.username]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return facilities;
    return facilities.filter((facility) => facility.facility_name.toLowerCase().includes(needle));
  }, [facilities, query]);

  if (!auth.ready) return <div className="auth-page"><div className="card auth-card"><p className="muted">Preparing facility selection…</p></div></div>;
  if (!auth.username || !getAccessToken()) return <Navigate to="/login" replace />;
  if (auth.facilityId && !auth.pendingFacilities) return <Navigate to="/" replace />;

  async function choose(facility: FacilityOption) {
    if (selecting) return;
    setSelecting(facility.facility_id);
    setError(null);
    try {
      await auth.selectFacility(facility);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Unable to open this facility.");
      setSelecting(null);
    }
  }

  return (
    <main className="auth-page facility-picker" aria-label="Select AfyaSync facility">
      <div className="card auth-card facility-picker-card">
        <div className="auth-brand">
          <div>
            <div className="brand-kicker">AfyaSync facility network</div>
            <h1>Choose your facility</h1>
          </div>
        </div>
        <p className="muted">Tap a facility to open its own AfyaSync dashboard. All clinical, financial and reporting activity will be scoped to the facility you select.</p>
        <label className="facility-search" htmlFor="facility-search">
          <span aria-hidden="true">⌕</span>
          <input id="facility-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by hospital, health centre or dispensary…" autoComplete="off" />
          {query && <button type="button" className="linkish" onClick={() => setQuery("")} aria-label="Clear facility search">Clear</button>}
        </label>
        {loading && <p className="muted">Loading facility network…</p>}
        {error && <div className="error" role="alert">{error}</div>}
        <div className="facility-picker-meta"><strong>{filtered.length.toLocaleString()}</strong><span>facilities available to this account</span></div>
        <div className="facility-grid">
          {filtered.map((facility) => (
            <button key={facility.facility_id} type="button" className="facility-card" onClick={() => void choose(facility)} disabled={Boolean(selecting)}>
              <span className="facility-card-icon" aria-hidden="true">+</span>
              <span className="facility-card-body"><strong>{facility.facility_name}</strong><span>Open facility dashboard</span></span>
              <span className="facility-card-arrow" aria-hidden="true">→</span>
              {selecting === facility.facility_id && <span className="facility-card-loading">Opening…</span>}
            </button>
          ))}
        </div>
        {!loading && filtered.length === 0 && <div className="card"><strong>No facility found</strong><p className="muted">Try a different hospital, health centre or dispensary name.</p></div>}
      </div>
    </main>
  );
}
