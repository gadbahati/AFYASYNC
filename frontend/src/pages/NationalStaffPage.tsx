import { useEffect, useState } from "react";
import { getNetworkFacilities, getNetworkStaff } from "../api/national";

export function NationalStaffPage() {
  const [staff, setStaff] = useState<Awaited<ReturnType<typeof getNetworkStaff>>>(null);
  const [facilities, setFacilities] = useState<Awaited<ReturnType<typeof getNetworkFacilities>>>([]);
  const [facilityId, setFacilityId] = useState("");
  const [status, setStatus] = useState("ACTIVE");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try { setStaff(await getNetworkStaff({ facilityId: facilityId || undefined, status: status || undefined })); }
    catch (err) { setError(err instanceof Error ? err.message : "NATIONAL_STAFF_REQUEST_FAILED"); }
    finally { setLoading(false); }
  }

  useEffect(() => { void getNetworkFacilities().then(setFacilities).catch(() => undefined); void load(); }, []);

  return <section className="page-stack">
    <div className="page-header"><div><p className="eyebrow">National administration</p><h1>Staff network</h1><p className="muted">Cross-facility workforce membership for network administration. Clinical records are not exposed.</p></div><button type="button" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button></div>
    {error && <div className="error-banner">{error === "PERMISSION_DENIED" ? "National staff administration permission required." : error}</div>}
    <div className="card"><div className="filter-row">
      <label>Status<select value={status} onChange={(e) => setStatus(e.target.value)}><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></label>
      <label>Facility<select value={facilityId} onChange={(e) => setFacilityId(e.target.value)}><option value="">All active facilities</option>{facilities.map((f) => <option key={f.id} value={f.id}>{f.name} ({f.facility_id})</option>)}</select></label>
      <button type="button" className="secondary filter-action" onClick={() => void load()}>Apply filters</button>
    </div></div>
    <div className="card"><div className="card-header"><div><h2>Network workforce</h2><p className="muted">Administrative staff membership only.</p></div>{staff && <span className="muted small">{staff.total} records</span>}</div>
      {loading ? <p className="muted">Loading staff network…</p> : !staff || staff.items.length === 0 ? <div className="empty-state"><strong>No staff found</strong><span>Adjust the filters or onboard staff at a facility.</span></div> : <div className="table-wrap"><table><thead><tr><th>Facility</th><th>Employee</th><th>Professional no.</th><th>Department</th><th>Status</th></tr></thead><tbody>{staff.items.map((item) => <tr key={item.id}><td><strong>{item.facility_name}</strong><div className="muted small">{item.facility_code}</div></td><td>{item.employee_number}</td><td>{item.professional_number || "—"}</td><td>{item.department_id || "—"}</td><td><span className="status-badge">{item.status}</span></td></tr>)}</tbody></table></div>}
    </div>
  </section>;
}
