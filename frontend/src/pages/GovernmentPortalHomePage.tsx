import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Overview = {
  data?: {
    organization?: { name: string; code: string; type: string };
    authorization?: { role_code: string; scope_level: string; facility_count: number; patient_identifiers_exposed: boolean };
    aggregates?: { facilities: number; patients: number; encounters: number; claims: number };
    facilities?: { id: string; name: string; county?: string | null }[];
    data_policy?: string;
  };
};

export function GovernmentPortalHomePage() {
  const auth = useAuth();
  const [overview, setOverview] = useState<Overview["data"] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.governmentOverview().then((r:any) => setOverview(r.data)).catch((e:any) => setError(e?.message || e?.code || "GOVERNMENT_OVERVIEW_FAILED"));
  }, []);

  return <main className="page">
    <div className="page-header">
      <div>
        <p className="muted">AFYASYNC GOVERNMENT PORTAL</p>
        <h1>{overview?.organization?.name || auth.governmentOrganization?.organization_name || "Government Health Workspace"}</h1>
        <p className="muted">Governed county and national health intelligence on the same AfyaSync core that powers participating facilities and patients.</p>
      </div>
      <button type="button" onClick={() => auth.logout().then(()=>window.location.assign("/login"))}>Sign out</button>
    </div>

    {error && <div className="error" role="alert">{error}</div>}

    <div className="card" style={{marginBottom:18}}>
      <h2>Authorized government context</h2>
      <p className="muted">Role: <strong>{overview?.authorization?.role_code || auth.governmentOrganization?.role_code || "—"}</strong> · Scope: <strong>{overview?.authorization?.scope_level || auth.governmentOrganization?.scope_level || "—"}</strong></p>
      <p className="muted small">Patient identifiers exposed by this overview: <strong>{overview?.authorization?.patient_identifiers_exposed ? "Yes" : "No"}</strong></p>
    </div>

    <div className="stat-grid" style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))",gap:12}}>
      {[
        ["Facilities", overview?.aggregates?.facilities ?? 0],
        ["Registered patients", overview?.aggregates?.patients ?? 0],
        ["Encounters", overview?.aggregates?.encounters ?? 0],
        ["Claims", overview?.aggregates?.claims ?? 0],
      ].map(([label,value])=><div className="stat-card" key={String(label)}><div className="muted small">{label}</div><div className="stat-value">{value}</div></div>)}
    </div>

    <div className="card-grid" style={{marginTop:18}}>
      <Link className="card" to="/government/facilities"><h2>Facility Network</h2><p className="muted">Authorized facility inventory and performance.</p></Link>
      <Link className="card" to="/government/analytics"><h2>Health Intelligence</h2><p className="muted">Aggregated service, financing and population-health intelligence.</p></Link>
      <Link className="card" to="/government/reporting"><h2>National Reporting</h2><p className="muted">Governed reporting and evidence workflows.</p></Link>
      <Link className="card" to="/government/interoperability"><h2>Interoperability</h2><p className="muted">HIE, FHIR, exchange and integration oversight.</p></Link>
      <Link className="card" to="/government/public-health"><h2>Public Health</h2><p className="muted">Surveillance, alerts and population-level monitoring.</p></Link>
      <Link className="card" to="/government/compliance"><h2>DHA / Compliance</h2><p className="muted">Security, privacy, audit and certification evidence.</p></Link>
    </div>

    <div className="card" style={{marginTop:18}}>
      <h2>Governance boundary</h2>
      <p className="muted">{overview?.data_policy || "Government views are governed by organization, role, scope and endpoint-level authorization."}</p>
    </div>
  </main>;
}
