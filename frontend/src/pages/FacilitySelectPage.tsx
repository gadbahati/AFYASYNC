import { useEffect, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { getAccessToken } from "../auth/storage";
import type { FacilityOption } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type DirectoryFacility = FacilityOption & {
  county?: string | null;
  sub_county?: string | null;
  facility_type?: string | null;
  registration_number?: string | null;
};

export function FacilitySelectPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [facilities, setFacilities] = useState<DirectoryFacility[]>(auth.pendingFacilities || []);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);

  async function loadDirectory(search: string, showSpinner = true) {
    if (showSpinner) setLoading(true);
    try {
      const rows = await api.facilityDirectory(search);
      setFacilities(rows as DirectoryFacility[]);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Unable to load the Kenya facility registry.");
    } finally {
      if (showSpinner) setLoading(false);
    }
  }

  useEffect(() => {
    if (!auth.ready || !auth.username || !getAccessToken()) return;
    void loadDirectory("");
    // The national import runs in the backend without blocking this screen.
    // Refresh while it is growing so newly imported facilities appear automatically.
    const timer = window.setInterval(() => {
      void loadDirectory(query, false);
    }, 10000);
    return () => window.clearInterval(timer);
  }, [auth.ready, auth.username]);

  useEffect(() => {
    if (!auth.ready || !auth.username || !getAccessToken()) return;
    const timer = window.setTimeout(() => void loadDirectory(query), 350);
    return () => window.clearTimeout(timer);
  }, [query]);

  if (!auth.ready) return <div className="auth-page"><div className="card auth-card"><p className="muted">Preparing facility selection…</p></div></div>;
  if (!auth.username || !getAccessToken()) return <Navigate to="/login" replace />;
  if (auth.facilityId && !auth.pendingFacilities) return <Navigate to="/" replace />;

  async function choose(facility: DirectoryFacility) {
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
            <div className="brand-kicker">AfyaSync national facility network</div>
            <h1>Choose your facility</h1>
          </div>
        </div>
        <p className="muted">Search the national Kenya health-facility registry, then open the selected facility's own AfyaSync workspace. Hospitals, referral facilities, health centres, dispensaries and clinics are included from the registry.</p>

        <label className="facility-search" htmlFor="facility-search">
          <span aria-hidden="true">⌕</span>
          <input id="facility-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search hospital, dispensary, health centre, clinic, county…" autoComplete="off" />
          {query && <button type="button" className="linkish" onClick={() => setQuery("")} aria-label="Clear facility search">Clear</button>}
        </label>

        <div className="facility-picker-meta">
          <strong>{facilities.length.toLocaleString()}</strong>
          <span>{query.trim() ? "matching facilities" : "active facilities currently indexed"}</span>
          <span className="muted">• The directory refreshes automatically while the national registry sync completes.</span>
        </div>

        {loading && <p className="muted">Loading facilities…</p>}
        {error && <div className="error" role="alert">{error}</div>}

        <div className="facility-grid">
          {facilities.map((facility) => (
            <button key={facility.facility_id} type="button" className="facility-card" onClick={() => void choose(facility)} disabled={Boolean(selecting)}>
              <span className="facility-card-icon" aria-hidden="true">+</span>
              <span className="facility-card-body">
                <strong>{facility.facility_name}</strong>
                <span>{[facility.facility_type, facility.sub_county, facility.county].filter(Boolean).join(" • ") || "Kenya health facility"}</span>
              </span>
              <span className="facility-card-arrow" aria-hidden="true">→</span>
              {selecting === facility.facility_id && <span className="facility-card-loading">Opening…</span>}
            </button>
          ))}
        </div>

        {!loading && facilities.length === 0 && (
          <div className="card"><strong>No facility found</strong><p className="muted">Try the facility name, county, sub-county, facility type or KMHFR facility code.</p></div>
        )}
      </div>
    </main>
  );
}
