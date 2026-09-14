import { useState, type FormEvent } from "react";
import { resolveNationalIdentity, NationalIdentityApiError } from "../api/nationalIdentityApi";
import type { NationalIdentityResolution } from "../api/nationalIdentity";

function displayDate(value: string | null) {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat("en-KE", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
}

export function NationalIdentityPage() {
  const [afyaId, setAfyaId] = useState("");
  const [identity, setIdentity] = useState<NationalIdentityResolution | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function resolve(event: FormEvent) {
    event.preventDefault();
    setLoading(true); setError(""); setIdentity(null);
    try {
      setIdentity(await resolveNationalIdentity(afyaId));
    } catch (err) {
      if (err instanceof NationalIdentityApiError) {
        setError(err.code === "AFYA_ID_NOT_FOUND" ? "No AfyaSync identity matched that Afya ID." : err.code === "PERMISSION_DENIED" ? "National identity permission is required for this workspace." : err.code);
      } else setError("NATIONAL_IDENTITY_REQUEST_FAILED");
    } finally { setLoading(false); }
  }

  return <section className="page-stack">
    <div className="page-header"><div><p className="eyebrow">National health identity</p><h1>Identity resolution</h1><p className="muted">Resolve an AfyaSync identity across the national network without exposing clinical or unnecessary personal information.</p></div></div>
    <div className="card"><div className="card-header"><div><h2>Resolve Afya ID</h2><p className="muted">Every lookup is audited. Use only for an authorised care, administration, or interoperability purpose.</p></div></div>
      <form className="form-grid" onSubmit={resolve}><label>Afya ID<input value={afyaId} onChange={(e) => setAfyaId(e.target.value.toUpperCase())} maxLength={20} minLength={1} required placeholder="Enter Afya ID" autoComplete="off" /></label><div className="form-actions"><button disabled={loading || !afyaId.trim()}>{loading ? "Resolving…" : "Resolve identity"}</button></div></form>
      {error && <div className="error-banner" role="alert">{error}</div>}
    </div>
    {identity && <div className="card"><div className="card-header"><div><p className="eyebrow">Identity match</p><h2>{identity.first_name} {identity.middle_name ? `${identity.middle_name} ` : ""}{identity.last_name}</h2><p className="muted">{identity.afya_id}</p></div><span className="status-badge">{identity.identity_status}</span></div><div className="stats-grid"><div className="metric-card"><span>Date of birth</span><strong>{displayDate(identity.date_of_birth)}</strong></div><div className="metric-card"><span>Sex</span><strong>{identity.sex || "Not recorded"}</strong></div><div className="metric-card"><span>Patient status</span><strong>{identity.patient_status}</strong></div><div className="metric-card"><span>Active facilities</span><strong>{identity.active_facility_count}</strong></div></div><p className="muted small">This national identity view intentionally excludes national ID numbers, phone numbers, addresses, next-of-kin details, and clinical records.</p></div>}
  </section>;
}
