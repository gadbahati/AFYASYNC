import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

type County = {
  county: string;
  facility_count: number;
  staff_count: number;
  encounters: number;
  claims: number;
  notifiable_events: number;
  ambulance_requests: number;
  teleconsult_requests: number;
  maturity_score: number;
  band: "GREEN" | "AMBER" | "RED";
};

type Evidence = {
  program?: string;
  phase?: number;
  national_totals?: { active_facilities?: number; active_staff?: number; encounters?: number; claims?: number; notifiable_events?: number };
  facility_slice?: { facility_id?: string; name?: string; county?: string; status?: string; staff?: number; encounters?: number; claims?: number } | null;
  evidence_checklist?: { id: string; label: string; status: string }[];
  generated_at?: string;
};

export function RolloutPage() {
  const [counties, setCounties] = useState<County[]>([]);
  const [bands, setBands] = useState<Record<string, number>>({});
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [limit, setLimit] = useState("50");
  const [includeFacility, setIncludeFacility] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [dashboard, pack] = await Promise.all([
        api.rolloutCountyDashboard(Number(limit)),
        api.rolloutPilotEvidence(includeFacility),
      ]);
      setCounties(dashboard.counties || []);
      setBands(dashboard.bands || {});
      setEvidence(pack || null);
    } catch (e: any) {
      setError(e?.message || "Rollout data could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [includeFacility, limit]);

  useEffect(() => { void load(); }, [load]);

  const totals = evidence?.national_totals || {};
  const averageScore = useMemo(
    () => counties.length ? (counties.reduce((sum, c) => sum + Number(c.maturity_score || 0), 0) / counties.length).toFixed(1) : "0.0",
    [counties],
  );

  return <section className="page-stack">
    <div className="page-heading">
      <div>
        <span className="eyebrow">PHASE 28 • COUNTY ROLLOUT</span>
        <h1>County rollout & pilot evidence</h1>
        <p className="muted">Operational visibility for county expansion and a consolidated evidence pack for pilot review.</p>
      </div>
      <button onClick={() => void load()} disabled={loading}>{loading ? "Refreshing…" : "Refresh"}</button>
    </div>

    {error && <div className="warning-box">{error}</div>}

    <div className="stat-grid">
      <div className="stat-card"><span className="eyebrow">ACTIVE FACILITIES</span><strong>{totals.active_facilities ?? "—"}</strong><span className="muted">National total</span></div>
      <div className="stat-card"><span className="eyebrow">ACTIVE STAFF</span><strong>{totals.active_staff ?? "—"}</strong><span className="muted">Current workforce</span></div>
      <div className="stat-card"><span className="eyebrow">ENCOUNTERS</span><strong>{totals.encounters ?? "—"}</strong><span className="muted">Recorded encounters</span></div>
      <div className="stat-card"><span className="eyebrow">CLAIMS</span><strong>{totals.claims ?? "—"}</strong><span className="muted">Recorded claims</span></div>
      <div className="stat-card"><span className="eyebrow">COUNTIES</span><strong>{counties.length}</strong><span className="muted">Average maturity {averageScore}</span></div>
    </div>

    <div className="card">
      <div className="row-between">
        <div><span className="eyebrow">ROLLOUT MONITOR</span><h2>County activity and maturity signals</h2></div>
        <span className="muted">{bands.GREEN || 0} green · {bands.AMBER || 0} amber · {bands.RED || 0} red</span>
      </div>
      <div className="form-grid">
        <label>Counties to show<select value={limit} onChange={e => setLimit(e.target.value)}><option value="25">25</option><option value="50">50</option><option value="100">100</option></select></label>
        <label className="checkbox-label"><input type="checkbox" checked={includeFacility} onChange={e => setIncludeFacility(e.target.checked)} /> Include current facility evidence slice</label>
      </div>
    </div>

    <div className="card">
      <div className="table-wrap">
        <table>
          <thead><tr><th>County</th><th>Facilities</th><th>Staff</th><th>Encounters</th><th>Claims</th><th>Surveillance</th><th>Ambulance</th><th>Teleconsult</th><th>Maturity</th><th>Band</th></tr></thead>
          <tbody>{counties.map(c => <tr key={c.county}>
            <td><strong>{c.county}</strong></td><td>{c.facility_count}</td><td>{c.staff_count}</td><td>{c.encounters}</td><td>{c.claims}</td><td>{c.notifiable_events}</td><td>{c.ambulance_requests}</td><td>{c.teleconsult_requests}</td><td>{c.maturity_score}</td><td><strong>{c.band}</strong></td>
          </tr>)}</tbody>
        </table>
      </div>
    </div>

    <div className="card-grid">
      <article className="card">
        <span className="eyebrow">PILOT EVIDENCE</span>
        <h2>Evidence checklist</h2>
        <div className="list-stack">{(evidence?.evidence_checklist || []).map(item =>
          <div className="row-between" key={item.id}><span><strong>{item.label}</strong><span className="small muted">{item.id}</span></span><span className="badge">{item.status}</span></div>
        )}</div>
      </article>
      <article className="card">
        <span className="eyebrow">FACILITY SLICE</span>
        <h2>{evidence?.facility_slice?.name || "Current facility"}</h2>
        {evidence?.facility_slice ? <div className="list-stack">
          <div className="row-between"><span className="muted">County</span><strong>{evidence.facility_slice.county || "—"}</strong></div>
          <div className="row-between"><span className="muted">Status</span><strong>{evidence.facility_slice.status || "—"}</strong></div>
          <div className="row-between"><span className="muted">Active staff</span><strong>{evidence.facility_slice.staff ?? 0}</strong></div>
          <div className="row-between"><span className="muted">Encounters</span><strong>{evidence.facility_slice.encounters ?? 0}</strong></div>
          <div className="row-between"><span className="muted">Claims</span><strong>{evidence.facility_slice.claims ?? 0}</strong></div>
        </div> : <p className="muted">Enable the facility evidence option to include the current facility slice.</p>}
      </article>
    </div>

    <div className="card">
      <span className="eyebrow">GOVERNANCE NOTE</span>
      <p className="muted">The maturity bands are operational signals produced by the Phase 28 rollout service. They are not a certification or regulatory approval. External penetration testing, production SHA credentials and DHA certification remain separately owned activities where indicated by the evidence checklist.</p>
      <p className="small muted">Evidence generated: {evidence?.generated_at ? new Date(evidence.generated_at).toLocaleString() : "—"}</p>
    </div>
  </section>;
}
