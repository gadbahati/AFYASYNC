import { useState } from "react";
import type { FormEvent } from "react";
import { getClinicalSummary } from "../api/interoperability";
import type { FHIRClinicalSummary } from "../api/interoperability";

export function InteroperabilityClinicalPage() {
  const [patientId, setPatientId] = useState("");
  const [reason, setReason] = useState("");
  const [result, setResult] = useState<FHIRClinicalSummary | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(""); setResult(null);
    if (!patientId.trim()) { setError("Enter a patient ID."); return; }
    if (reason.trim().length < 3) { setError("A clear access reason is required."); return; }
    setLoading(true);
    try { setResult(await getClinicalSummary(patientId.trim(), reason)); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to retrieve the clinical summary."); }
    finally { setLoading(false); }
  }

  return <main className="page-shell">
    <header className="page-header">
      <div><p className="eyebrow">INTEROPERABILITY</p><h1>Clinical exchange</h1><p>Retrieve a minimum necessary, facility-scoped FHIR summary for an authorised care workflow.</p></div>
    </header>
    <section className="card">
      <form onSubmit={submit}>
        <label>Patient ID<input value={patientId} onChange={e => setPatientId(e.target.value)} maxLength={36} placeholder="Patient UUID" /></label>
        <label>Access reason<textarea value={reason} onChange={e => setReason(e.target.value)} maxLength={200} placeholder="Why is this clinical summary required?" /></label>
        <button type="submit" disabled={loading}>{loading ? "Retrieving…" : "Retrieve summary"}</button>
      </form>
      {error && <p role="alert">{error}</p>}
    </section>
    {result && <section className="card"><h2>FHIR summary</h2><p>{result.total} resources returned. Patient demographics and encounter metadata only.</p><div>{result.entry.map(entry => <article key={entry.fullUrl}><strong>{entry.resource.resourceType}</strong><span> {entry.resource.id}</span></article>)}</div><p>Access is facility-scoped and audited. Clinical notes, diagnoses, laboratory results, prescriptions, billing and contacts are not exported by this endpoint.</p></section>}
  </main>;
}
