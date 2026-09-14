import { useEffect, useRef, useState } from "react";
import { getNationalCapacity } from "../api/nationalCapacityApi";
import type { NationalCapacity } from "../api/nationalCapacity";

export function NationalCapacityPage() {
  const [data, setData] = useState<NationalCapacity | null>(null);
  const [county, setCounty] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const requestRef = useRef(0);

  async function load() {
    const requestId = ++requestRef.current;
    setLoading(true); setError("");
    try {
      const result = await getNationalCapacity(county);
      if (requestId !== requestRef.current) return;
      setData(result);
    } catch (err) {
      if (requestId !== requestRef.current) return;
      setError(err instanceof Error ? err.message : "NATIONAL_CAPACITY_REQUEST_FAILED");
    } finally {
      if (requestId === requestRef.current) setLoading(false);
    }
  }

  useEffect(() => { void load(); return () => { requestRef.current += 1; }; }, []);

  return <section className="page-stack">
    <header className="page-heading">
      <div><p className="eyebrow">National care operations</p><h1>Clinical capacity</h1><p className="muted">Current operational capacity across active facilities. No patient-level information is exposed.</p></div>
      <button type="button" className="button secondary" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button>
    </header>
    <article className="card"><div className="filter-row"><label>County<input maxLength={100} value={county} placeholder="All counties" onChange={event => setCounty(event.target.value)} /></label><button type="button" className="button filter-action" onClick={() => void load()} disabled={loading}>Apply filter</button></div></article>
    {error && <div className="error-banner" role="alert">{error === "PERMISSION_DENIED" ? "National reporting permission required." : error}</div>}
    <div className="metrics-grid">
      <article className="card metric-card"><span className="muted">Active facilities</span><strong>{data?.active_facilities.toLocaleString() ?? "—"}</strong></article>
      <article className="card metric-card"><span className="muted">Active departments</span><strong>{data?.active_departments.toLocaleString() ?? "—"}</strong></article>
      <article className="card metric-card"><span className="muted">Appointments next 7 days</span><strong>{data?.scheduled_appointments.toLocaleString() ?? "—"}</strong></article>
      <article className="card metric-card"><span className="muted">Patients waiting</span><strong>{data?.waiting_queue_entries.toLocaleString() ?? "—"}</strong></article>
    </div>
    <article className="card"><div className="card-header"><div><h2>Facility capacity</h2><p className="muted">Department availability, scheduled demand and current waiting queue size.</p></div></div>{loading ? <p className="muted">Loading capacity…</p> : !data?.facilities.length ? <div className="empty-state"><strong>No active facilities found</strong><span>Adjust the county filter or confirm facility network status.</span></div> : <div className="table-wrap"><table><thead><tr><th>Facility</th><th>County</th><th>Departments</th><th>Appointments</th><th>Waiting</th></tr></thead><tbody>{data.facilities.map(facility => <tr key={facility.facility_id}><td><strong>{facility.facility_name}</strong><div className="muted small">{facility.facility_code}</div></td><td>{facility.county || "Unspecified"}</td><td>{facility.departments.toLocaleString()}</td><td>{facility.scheduled_appointments.toLocaleString()}</td><td>{facility.waiting_queue_entries.toLocaleString()}</td></tr>)}</tbody></table></div>}</article>
  </section>;
}
