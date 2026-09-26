import { useState } from "react";
import { api } from "../api/client";

export function UniversalIdentityPage() {
  const [mode,setMode]=useState<"resolve"|"register">("resolve");
  const [type,setType]=useState("PHONE");
  const [identifier,setIdentifier]=useState("");
  const [personId,setPersonId]=useState("");
  const [payerId,setPayerId]=useState("");
  const [result,setResult]=useState<any>(null);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(false);

  async function submit() {
    setLoading(true); setError(""); setResult(null);
    try {
      const base:any={identifier_type:type,identifier:identifier.trim(),payer_id:payerId.trim()||null};
      const out=mode==="register"
        ? await api.financingIdentityRegister({...base,person_id:personId.trim()})
        : await api.financingIdentityResolve(base);
      setResult(out);
    } catch(err) { setError(err instanceof Error ? err.message : "IDENTITY_REQUEST_FAILED"); }
    finally { setLoading(false); }
  }

  return <section className="page-stack">
    <div className="page-header"><div><p className="eyebrow">Phase 43 · Universal financing identity</p><h1>Identity resolution exchange</h1><p className="muted">Resolve a person across Afya ID, payer membership, phone and protected national identifiers without storing the raw identifier in this financing index.</p></div></div>
    {error && <div className="error-banner">{error}</div>}
    <div className="card">
      <div className="card-header"><div><p className="eyebrow">Identity operation</p><h2>{mode==="resolve"?"Resolve a person":"Bind an identifier"}</h2></div><span className="status-badge">PROTECTED LOOKUP</span></div>
      <div className="form-actions"><button type="button" className={mode==="resolve"?"primary":"secondary"} onClick={()=>setMode("resolve")}>Resolve</button><button type="button" className={mode==="register"?"primary":"secondary"} onClick={()=>setMode("register")}>Register binding</button></div>
      <div className="form-grid">
        <label>Identifier type<select value={type} onChange={e=>setType(e.target.value)}><option>PHONE</option><option>AFYA_ID</option><option>PAYER_MEMBER</option><option>NATIONAL_ID_HASH</option></select></label>
        <label>Identifier<input value={identifier} onChange={e=>setIdentifier(e.target.value)} placeholder="Enter identifier" /></label>
        <label>Payer ID <span className="muted small">(optional)</span><input value={payerId} onChange={e=>setPayerId(e.target.value)} placeholder="UUID" /></label>
        {mode==="register" && <label>Person ID<input value={personId} onChange={e=>setPersonId(e.target.value)} placeholder="UUID" /></label>}
      </div>
      <div className="form-actions"><button type="button" className="primary" disabled={loading||!identifier.trim()||(mode==="register"&&!personId.trim())} onClick={()=>void submit()}>{loading?"Working…":mode==="resolve"?"Resolve identity":"Register identity"}</button></div>
    </div>
    {result && <div className="card"><div className="card-header"><div><p className="eyebrow">Resolution</p><h2>{result.status}</h2></div><span className="status-badge">{result.conflict?"CONFLICT CHECK REQUIRED":"NO CONFLICT"}</span></div><div className="stat-grid"><div className="stat-card"><span>Matched person</span><strong>{result.person_id?"MATCH":"—"}</strong><small>{result.person_id||"No single person resolved"}</small></div><div className="stat-card"><span>Candidates</span><strong>{result.match_count}</strong><small>Distinct people found</small></div><div className="stat-card"><span>Identifier</span><strong>{result.identifier_type}</strong><small>Normalized before hashing</small></div><div className="stat-card"><span>Payer scope</span><strong>{result.payer_id?"SCOPED":"GLOBAL"}</strong><small>Financing participant context</small></div></div><div className="notice-box"><strong>Evidence</strong><span>{JSON.stringify(result.evidence||{})}</span></div></div>}
    <div className="card"><p className="eyebrow">Why this matters</p><h2>One person, many financing relationships</h2><p className="muted">The identity layer separates the citizen from the payer. A person can carry SHA coverage, private insurance, employer financing or other payer relationships while the platform retains one canonical financing identity.</p></div>
  </section>;
}
