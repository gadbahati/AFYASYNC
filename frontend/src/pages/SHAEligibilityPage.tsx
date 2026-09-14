import { useState, type FormEvent } from "react";
import { checkSHAEligibility, SHAEligibilityApiError } from "../api/shaEligibilityApi";
import type { SHAEligibilityResponse } from "../api/shaEligibility";

function formatDate(value: string | null) {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat("en-KE", { dateStyle: "medium" }).format(new Date(`${value}T00:00:00`));
}

export function SHAEligibilityPage() {
  const [personId, setPersonId] = useState("");
  const [membership, setMembership] = useState("");
  const [result, setResult] = useState<SHAEligibilityResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setResult(null);
    setBusy(true);
    try {
      setResult(await checkSHAEligibility(personId.trim(), membership));
    } catch (err) {
      setError(err instanceof SHAEligibilityApiError ? err.code : "SHA_ELIGIBILITY_REQUEST_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Coverage</p>
          <h1>SHA eligibility verification</h1>
          <p className="muted">Verify SHA coverage through the facility's explicitly configured payer connector. No local success is assumed when SHA is unavailable.</p>
        </div>
      </header>

      <form className="card form-grid" onSubmit={submit}>
        <label>Patient person ID<input value={personId} onChange={(event) => setPersonId(event.target.value)} required placeholder="Patient UUID" autoComplete="off" /></label>
        <label>SHA membership number<input value={membership} onChange={(event) => setMembership(event.target.value.toUpperCase())} required maxLength={100} placeholder="SHA / SHIF membership number" autoComplete="off" /></label>
        <div className="form-actions"><button disabled={busy || !personId.trim() || !membership.trim()}>{busy ? "Checking…" : "Verify with SHA"}</button></div>
        {error && <div className="error-banner" role="alert">{error}</div>}
      </form>

      {result && (
        <div className="card">
          <div className="card-header"><div><p className="eyebrow">Payer response</p><h2>{result.eligible ? "Eligible" : "Not eligible"}</h2><p className="muted">Membership {result.membership_number}</p></div><span className="status-badge">{result.verification_status}</span></div>
          <div className="stats-grid">
            <div className="metric-card"><span>Coverage start</span><strong>{formatDate(result.start_date)}</strong></div>
            <div className="metric-card"><span>Coverage end</span><strong>{formatDate(result.end_date)}</strong></div>
            <div className="metric-card"><span>External reference</span><strong>{result.external_reference || "Not supplied"}</strong></div>
          </div>
          <p className="muted small">The connector response is the source of verification. If the payer service is unavailable, AfyaSync does not convert the failure into an eligible result.</p>
        </div>
      )}
    </section>
  );
}
