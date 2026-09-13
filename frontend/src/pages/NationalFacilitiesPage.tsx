import { useEffect, useState, type FormEvent } from "react";
import {
  createNetworkFacility,
  getNetworkFacilities,
  updateNetworkFacilityStatus,
  type NetworkFacilityInput,
} from "../api/national";

type FacilityStatus = "APPLICATION" | "ACTIVE" | "SUSPENDED" | "INACTIVE";

const emptyForm: NetworkFacilityInput = {
  name: "",
  facility_type: "",
  registration_number: null,
  license_number: null,
  county: null,
  sub_county: null,
  address: null,
  phone: null,
  email: null,
};

function display(value: string | null) {
  return value?.trim() || "—";
}

export function NationalFacilitiesPage() {
  const [facilities, setFacilities] = useState<Awaited<ReturnType<typeof getNetworkFacilities>>>([]);
  const [status, setStatus] = useState("");
  const [county, setCounty] = useState("");
  const [form, setForm] = useState<NetworkFacilityInput>(emptyForm);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setFacilities(await getNetworkFacilities({ status: status || undefined, county: county || undefined }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "NATIONAL_FACILITY_REQUEST_FAILED");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await createNetworkFacility({
        ...form,
        registration_number: form.registration_number?.trim() || null,
        license_number: form.license_number?.trim() || null,
        county: form.county?.trim() || null,
        sub_county: form.sub_county?.trim() || null,
        address: form.address?.trim() || null,
        phone: form.phone?.trim() || null,
        email: form.email?.trim() || null,
      });
      setForm(emptyForm);
      setShowCreate(false);
      setMessage("Facility registered in the national network.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "NATIONAL_FACILITY_REQUEST_FAILED");
    } finally {
      setSaving(false);
    }
  }

  async function changeStatus(facilityId: string, next: FacilityStatus) {
    setError("");
    setMessage("");
    try {
      await updateNetworkFacilityStatus(facilityId, next);
      setMessage(`Facility status changed to ${next}.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "NATIONAL_FACILITY_REQUEST_FAILED");
    }
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">National administration</p>
          <h1>Facility network</h1>
          <p className="muted">Manage the trusted facility registry used by the national AfyaSync network.</p>
        </div>
        <button type="button" onClick={() => setShowCreate((value) => !value)}>
          {showCreate ? "Close registration" : "Register facility"}
        </button>
      </div>

      {error && <div className="error-banner">{error === "PERMISSION_DENIED" ? "National facility administration permission required." : error}</div>}
      {message && <div className="success-banner">{message}</div>}

      {showCreate && (
        <form className="card form-grid" onSubmit={submit}>
          <div className="card-header"><div><h2>Register facility</h2><p className="muted">Creates a real facility record. New facilities start in APPLICATION status.</p></div></div>
          <label>Facility name<input required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
          <label>Facility type<input required minLength={2} value={form.facility_type} onChange={(e) => setForm({ ...form, facility_type: e.target.value })} /></label>
          <label>Registration number<input value={form.registration_number ?? ""} onChange={(e) => setForm({ ...form, registration_number: e.target.value })} /></label>
          <label>License number<input value={form.license_number ?? ""} onChange={(e) => setForm({ ...form, license_number: e.target.value })} /></label>
          <label>County<input value={form.county ?? ""} onChange={(e) => setForm({ ...form, county: e.target.value })} /></label>
          <label>Sub-county<input value={form.sub_county ?? ""} onChange={(e) => setForm({ ...form, sub_county: e.target.value })} /></label>
          <label>Phone<input value={form.phone ?? ""} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></label>
          <label>Email<input type="email" value={form.email ?? ""} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
          <label className="full-width">Address<textarea rows={2} value={form.address ?? ""} onChange={(e) => setForm({ ...form, address: e.target.value })} /></label>
          <div className="form-actions full-width"><button disabled={saving}>{saving ? "Registering…" : "Register facility"}</button></div>
        </form>
      )}

      <div className="card">
        <div className="card-header">
          <div><h2>Network directory</h2><p className="muted">Cross-facility administrative metadata only; no patient records are exposed here.</p></div>
          <button type="button" className="secondary" onClick={() => void load()} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button>
        </div>
        <div className="filter-row">
          <label>Status<select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option value="APPLICATION">Application</option><option value="ACTIVE">Active</option><option value="SUSPENDED">Suspended</option><option value="INACTIVE">Inactive</option></select></label>
          <label>County<input value={county} placeholder="Filter county" onChange={(e) => setCounty(e.target.value)} /></label>
          <button type="button" className="secondary filter-action" onClick={() => void load()}>Apply filters</button>
        </div>

        {loading ? <p className="muted">Loading facility network…</p> : facilities.length === 0 ? <div className="empty-state"><strong>No facilities found</strong><span>Adjust the filters or register the first facility.</span></div> : (
          <div className="table-wrap"><table><thead><tr><th>Facility</th><th>Location</th><th>Type</th><th>Status</th><th>Identifiers</th><th>Actions</th></tr></thead><tbody>
            {facilities.map((facility) => <tr key={facility.id}>
              <td><strong>{facility.name}</strong><div className="muted small">{facility.facility_id}</div></td>
              <td>{display(facility.county)}<div className="muted small">{display(facility.sub_county)}</div></td>
              <td>{facility.facility_type}</td>
              <td><span className="status-badge">{facility.status}</span></td>
              <td><div>{display(facility.registration_number)}</div><div className="muted small">{display(facility.license_number)}</div></td>
              <td><div className="button-row">
                {facility.status !== "ACTIVE" && <button type="button" className="secondary compact" onClick={() => void changeStatus(facility.id, "ACTIVE")}>Activate</button>}
                {facility.status === "ACTIVE" && <button type="button" className="secondary compact" onClick={() => void changeStatus(facility.id, "SUSPENDED")}>Suspend</button>}
                {facility.status !== "INACTIVE" && <button type="button" className="secondary compact" onClick={() => void changeStatus(facility.id, "INACTIVE")}>Inactivate</button>}
              </div></td>
            </tr>)}
          </tbody></table></div>
        )}
      </div>
    </section>
  );
}
