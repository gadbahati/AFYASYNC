import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../api/client";

type Overview = {
  organization?: { name: string; code: string; type: string };
  authorization?: { role_code: string; scope_level: string; facility_count: number; patient_identifiers_exposed: boolean };
  aggregates?: { facilities: number; patients: number; encounters: number; claims: number };
  facilities?: { id: string; name: string; county?: string | null; status?: string }[];
  data_policy?: string;
};

const labels: Record<string, string> = {
  facilities: "Facility Network",
  analytics: "Health Intelligence",
  reporting: "National Reporting",
  interoperability: "Interoperability",
  "public-health": "Public Health",
  compliance: "DHA / Compliance",
};

const descriptions: Record<string, string> = {
  facilities: "Authorized facilities attached to the government organization.",
  analytics: "Governed aggregate service and financing intelligence.",
  reporting: "Current governed reporting totals available to this organization.",
  interoperability: "The government view of the national exchange boundary and its governed data scope.",
  "public-health": "Population-level operational signals available through the government authorization boundary.",
  compliance: "Governance, authorization and data-protection posture for this government workspace.",
};

export function GovernmentModulePage() {
  const location = useLocation();
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");
  const key = location.pathname.split("/").filter(Boolean).pop() || "";
  const label = labels[key] || "Government Workspace";

  useEffect(() => {
    let cancelled = false;
    api.governmentOverview()
      .then((response: any) => {
        if (!cancelled) setData(response?.data || null);
      })
      .catch((e: any) => {
        if (!cancelled) setError(e?.message || e?.code || "Unable to load government data.");
      });
    return () => { cancelled = true; };
  }, []);

  const aggregateRows = useMemo(() => [
    ["Facilities", data?.aggregates?.facilities ?? 0],
    ["Registered patients", data?.aggregates?.patients ?? 0],
    ["Encounters", data?.aggregates?.encounters ?? 0],
    ["Claims", data?.aggregates?.claims ?? 0],
  ], [data]);

  return (
    <main className="page">
      <div className="page-header">
        <div>
          <p className="muted">GOVERNMENT PORTAL</p>
          <h1>{label}</h1>
          <p className="muted">{descriptions[key] || "Governed government health workspace."}</p>
        </div>
        <Link to="/government">← Government portal</Link>
      </div>

      {error && <div className="error" role="alert">{error}</div>}

      <section className="card">
        <h2>Authorized context</h2>
        <p className="muted">
          Organization: <strong>{data?.organization?.name || "—"}</strong>
          {" · "}Role: <strong>{data?.authorization?.role_code || "—"}</strong>
          {" · "}Scope: <strong>{data?.authorization?.scope_level || "—"}</strong>
        </p>
        <p className="small muted">
          Patient identifiers exposed by this government overview: <strong>{data?.authorization?.patient_identifiers_exposed ? "Yes" : "No"}</strong>
        </p>
      </section>

      <section className="stat-grid" style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(160px,1fr))",gap:12,marginTop:18}}>
        {aggregateRows.map(([name, value]) => (
          <div className="stat-card" key={name}>
            <span className="muted small">{name}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </section>

      {key === "facilities" && (
        <section className="card" style={{marginTop:18}}>
          <h2>Facilities in authorized scope</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Facility</th><th>County</th><th>Status</th></tr></thead>
              <tbody>
                {(data?.facilities || []).map((facility) => (
                  <tr key={facility.id}><td>{facility.name}</td><td>{facility.county || "—"}</td><td>{facility.status || "—"}</td></tr>
                ))}
                {!data?.facilities?.length && <tr><td colSpan={3} className="muted">No authorized facilities are currently attached.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {key !== "facilities" && (
        <section className="card" style={{marginTop:18}}>
          <h2>Current governed snapshot</h2>
          <p className="muted">
            These figures are live aggregates returned by the government authorization endpoint. More detailed
            records remain protected behind their own endpoint permissions and lawful-purpose controls.
          </p>
          <div className="list-stack">
            <div className="row-between"><span>Data policy</span><strong>{data?.data_policy || "Governed aggregates by default."}</strong></div>
            <div className="row-between"><span>Organization code</span><strong>{data?.organization?.code || "—"}</strong></div>
            <div className="row-between"><span>Facilities in scope</span><strong>{data?.authorization?.facility_count ?? 0}</strong></div>
          </div>
        </section>
      )}
    </main>
  );
}
