import { useEffect, useRef, useState } from "react";
import { getNationalCapacity, getNationalServiceCapacity } from "../api/nationalCapacityApi";
import type { NationalCapacity } from "../api/nationalCapacity";

export function NationalCapacityPage() {
  const [data, setData] = useState<NationalCapacity | null>(null);
  const [county, setCounty] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [services, setServices] = useState<any[]>([]);
  const [serviceCode, setServiceCode] = useState("");
  const [serviceLoading, setServiceLoading] = useState(false);
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
  async function loadServices() {
    setServiceLoading(true); setError("");
    try { setServices(await getNationalServiceCapacity({ service_code: serviceCode, county })); }
    catch (err) { setError(err instanceof Error ? err.message : "NATIONAL_SERVICE_CAPACITY_REQUEST_FAILED"); }
    finally { setServiceLoading(false); }
  }

  const occupancyRate = data && data.total_beds > 0 ? Math.round((data.occupied_beds / data.total_beds) * 100) : 0;

  return <section className="page-stack">
    <header className="page-heading">
      <div><p className="eyebrow">National care operations</p><h1>Clinical capacity</h1><p className="muted">Live operational capacity across active facilities, using authoritative facility, ward, bed, queue and emergency records. No patient-level information is exposed.</p></div>
      <button type="button" className="button secondary" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button>
    </header>
    <article className="card"><div className="filter-row"><label>County<input maxLength={100} value={county} placeholder="All counties" onChange={event => setCounty(event.target.value)} /></label><button type="button" className="button filter-action" onClick={() => void load()} disabled={loading}>Apply filter</button></div></article>
    {error && <div className="error-banner" role="alert">{error === "PERMISSION_DENIED" ? "National reporting permission required." : error}</div>}
    <div className="metrics-grid">
      <article className="card metric-card"><span className="muted">Active facilities</span><strong>{data?.active_facilities.toLocaleString() ?? "—"}</strong></article>
      <article className="card metric-card"><span className="muted">Available beds</span><strong>{data?.available_beds.toLocaleString() ?? "—"}</strong><small className="muted">of {data?.total_beds.toLocaleString() ?? "—"} total</small></article>
      <article className="card metric-card"><span className="muted">Bed occupancy</span><strong>{data ? `${occupancyRate}%` : "—"}</strong><small className="muted">{data?.occupied_beds.toLocaleString() ?? "—"} occupied</small></article>
      <article className="card metric-card"><span className="muted">Emergency load</span><strong>{data?.emergency_waiting.toLocaleString() ?? "—"}</strong><small className="muted">active emergency visits</small></article>
      <article className="card metric-card"><span className="muted">Active departments</span><strong>{data?.active_departments.toLocaleString() ?? "—"}</strong></article>
      <article className="card metric-card"><span className="muted">Patients waiting</span><strong>{data?.waiting_queue_entries.toLocaleString() ?? "—"}</strong></article>
    </div>
    <article className="card"><div className="card-header"><div><h2>Service capacity exchange</h2><p className="muted">Search active provider-network services by service code and see daily appointment capacity across facilities.</p></div></div>
      <div className="filter-row"><label>Service code<input value={serviceCode} maxLength={80} placeholder="e.g. CONSULT" onChange={event => setServiceCode(event.target.value)} /></label><button type="button" className="button filter-action" onClick={() => void loadServices()} disabled={serviceLoading}>{serviceLoading ? "Searching…" : "Search service capacity"}</button></div>
      {services.length > 0 && <div className="table-wrap"><table><thead><tr><th>Facility</th><th>Service</th><th>Network</th><th>Date</th><th>Capacity</th><th>Booked</th><th>Remaining</th><th>Status</th></tr></thead><tbody>{services.map(item => <tr key={item.facility_id + item.service_code + item.network_code}><td><strong>{item.facility_name}</strong><div className="muted small">{item.county || "Unspecified"}</div></td><td>{item.service_name}<div className="muted small">{item.service_code}</div></td><td>{item.network_code}</td><td>{item.date}</td><td>{item.daily_capacity}</td><td>{item.booked}</td><td>{item.remaining}</td><td>{item.availability}</td></tr>)}</tbody></table></div>}
    </article>
    <article className="card"><div className="card-header"><div><h2>Facility capacity</h2><p className="muted">Operational demand and inpatient capacity by active facility.</p></div></div>{loading ? <p className="muted">Loading capacity…</p> : !data?.facilities.length ? <div className="empty-state"><strong>No active facilities found</strong><span>Adjust the county filter or confirm facility network status.</span></div> : <div className="table-wrap"><table><thead><tr><th>Facility</th><th>County</th><th>Beds</th><th>Available</th><th>Occupied</th><th>Emergency</th><th>Waiting</th></tr></thead><tbody>{data.facilities.map(facility => <tr key={facility.facility_id}><td><strong>{facility.facility_name}</strong><div className="muted small">{facility.facility_code}</div></td><td>{facility.county || "Unspecified"}</td><td>{facility.total_beds.toLocaleString()}</td><td>{facility.available_beds.toLocaleString()}</td><td>{facility.occupied_beds.toLocaleString()}</td><td>{facility.emergency_waiting.toLocaleString()}</td><td>{facility.waiting_queue_entries.toLocaleString()}</td></tr>)}</tbody></table></div>}</article>
  </section>;
}
