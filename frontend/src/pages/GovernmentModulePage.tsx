import { useLocation, Link } from "react-router-dom";

const labels: Record<string,string> = {
  facilities: "Facility Network",
  analytics: "Health Intelligence",
  reporting: "National Reporting",
  interoperability: "Interoperability",
  "public-health": "Public Health",
  compliance: "DHA / Compliance",
};

export function GovernmentModulePage() {
  const location = useLocation();
  const key = location.pathname.split("/").filter(Boolean).pop() || "";
  const label = labels[key] || "Government Module";
  return <main className="page">
    <div className="page-header"><div><p className="muted">GOVERNMENT PORTAL</p><h1>{label}</h1><p className="muted">This module is attached to the governed Government Portal and AfyaSync national core.</p></div></div>
    <div className="card">
      <h2>Government authorization boundary</h2>
      <p className="muted">The module will only expose data permitted by your government organization, role, scope and endpoint-level permissions. It is not activated by a facility scope switch.</p>
      <Link to="/government">← Back to Government Portal</Link>
    </div>
  </main>;
}
