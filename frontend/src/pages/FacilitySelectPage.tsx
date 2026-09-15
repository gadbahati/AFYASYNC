import { useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { getAccessToken } from "../auth/storage";
import type { FacilityOption } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type DirectoryFacility = FacilityOption & { facility_code?: string | null; county?: string | null; sub_county?: string | null; facility_type?: string | null; keph_level?: string | number | null; owner?: string | null; operation_status?: string | null; registration_number?: string | null };
const PAGE_SIZE = 50;

export function FacilitySelectPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [facilities, setFacilities] = useState<DirectoryFacility[]>(auth.pendingFacilities || []);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [selecting, setSelecting] = useState<string | null>(null);

  async function loadDirectory(search: string, showSpinner = true) {
    if (showSpinner) setLoading(true);
    try { setFacilities((await api.facilityDirectory(search)) as DirectoryFacility[]); setPage(1); setError(null); }
    catch (err) { setError(err instanceof ApiError ? err.message || err.code : "Unable to load the Kenya health-facility registry."); }
    finally { if (showSpinner) setLoading(false); }
  }

  useEffect(() => {
    if (!auth.ready || !auth.username || !getAccessToken()) return;
    void loadDirectory("");
    const timer = window.setInterval(() => void loadDirectory(submittedQuery, false), 30000);
    return () => window.clearInterval(timer);
  }, [auth.ready, auth.username]);

  const visibleFacilities = useMemo(() => facilities.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [facilities, page]);
  const pageCount = Math.max(1, Math.ceil(facilities.length / PAGE_SIZE));

  if (!auth.ready) return <div className="auth-page"><div className="card auth-card"><p className="muted">Preparing facility selection…</p></div></div>;
  if (!auth.username || !getAccessToken()) return <Navigate to="/login" replace />;
  if (auth.facilityId && !auth.pendingFacilities) return <Navigate to="/" replace />;

  async function searchFacilities(event: React.FormEvent) { event.preventDefault(); const value = query.trim(); setSubmittedQuery(value); await loadDirectory(value); }
  async function choose(facility: DirectoryFacility) {
    if (selecting) return; setSelecting(facility.facility_id); setError(null);
    try { await auth.selectFacility(facility); navigate("/", { replace: true }); }
    catch (err) { setError(err instanceof ApiError ? err.message || err.code : "Unable to open this facility."); setSelecting(null); }
  }

  return (
    <main className="auth-page" aria-label="AfyaSync national facility directory" style={{ padding: "28px 16px", alignItems: "flex-start" }}>
      <section className="card" style={{ width: "min(1500px,100%)", padding: 28, overflow: "hidden" }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 20, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 20 }}>
          <div><div className="brand-kicker">AfyaSync • Kenya health-facility directory</div><h1 style={{ marginBottom: 8 }}>Select a facility</h1><p className="muted" style={{ margin: 0 }}>All active facilities imported from the national KMHFR registry are listed below.</p></div>
          <strong>{facilities.length.toLocaleString()} facilities indexed</strong>
        </div>
        <form onSubmit={searchFacilities} style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 18 }}>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search hospital, dispensary, health centre, clinic, county, sub-county or MFL code…" autoComplete="off" style={{ flex: "1 1 420px", minWidth: 0, height: 46, padding: "0 14px", border: "1px solid #cbd5e1", borderRadius: 10, fontSize: 15 }} />
          <button type="submit" disabled={loading} style={{ height: 46, padding: "0 24px", border: 0, borderRadius: 10, fontWeight: 700 }}>{loading ? "Searching…" : "Search"}</button>
          {submittedQuery && <button type="button" onClick={() => { setQuery(""); setSubmittedQuery(""); void loadDirectory(""); }}>Clear</button>}
        </form>
        {error && <div className="error" role="alert" style={{ marginBottom: 16 }}>{error}</div>}
        <div style={{ overflowX: "auto", border: "1px solid #e2e8f0", borderRadius: 12 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 1000 }}>
            <thead><tr style={{ textAlign: "left", borderBottom: "2px solid #e2e8f0" }}>{["Facility name","MFL code","Type","KEPH","County","Sub-county","Owner","Status",""].map(h => <th key={h} style={{ padding: "13px 14px", fontSize: 12, textTransform: "uppercase", whiteSpace: "nowrap" }}>{h}</th>)}</tr></thead>
            <tbody>{visibleFacilities.map(f => <tr key={f.facility_id} onClick={() => void choose(f)} style={{ borderBottom: "1px solid #edf2f7", cursor: "pointer" }}>
              <td style={{ padding: 14, fontWeight: 700 }}>{f.facility_name}</td><td style={{ padding: 14 }}>{f.facility_code || f.registration_number || "—"}</td><td style={{ padding: 14 }}>{f.facility_type || "—"}</td><td style={{ padding: 14 }}>{f.keph_level ? `Level ${f.keph_level}` : "—"}</td><td style={{ padding: 14 }}>{f.county || "—"}</td><td style={{ padding: 14 }}>{f.sub_county || "—"}</td><td style={{ padding: 14 }}>{f.owner || "—"}</td><td style={{ padding: 14 }}>{f.operation_status || "ACTIVE"}</td><td style={{ padding: 14 }}><button type="button" onClick={e => { e.stopPropagation(); void choose(f); }} disabled={Boolean(selecting)}>Open</button></td>
            </tr>)}</tbody>
          </table>
        </div>
        {!loading && facilities.length === 0 && <div className="card" style={{ marginTop: 16 }}><strong>No facility found</strong><p className="muted">Try the official facility name, MFL code, county, sub-county or facility type.</p></div>}
        {facilities.length > 0 && <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap", marginTop: 16 }}><span className="muted">Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, facilities.length)} of {facilities.length}</span><div style={{ display: "flex", gap: 8 }}><button type="button" disabled={page === 1} onClick={() => setPage(p => p - 1)}>Previous</button><strong style={{ padding: "8px 4px" }}>Page {page} of {pageCount}</strong><button type="button" disabled={page === pageCount} onClick={() => setPage(p => p + 1)}>Next</button></div></div>}
      </section>
    </main>
  );
}
