import { useState } from "react";
import { api } from "../api/client";

export function EligibilityEnginePage() {
  const [personId, setPersonId] = useState("");
  const [payerId, setPayerId] = useState("");
  const [payerPlanId, setPayerPlanId] = useState("");
  const [serviceCode, setServiceCode] = useState("");
  const [serviceType, setServiceType] = useState("");
  const [grossAmount, setGrossAmount] = useState("0");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function evaluate() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const payload: any = {
        person_id: personId.trim(),
        service_code: serviceCode.trim() || null,
        service_type: serviceType.trim() || null,
        payer_id: payerId.trim() || null,
        payer_plan_id: payerPlanId.trim() || null,
        gross_amount: Number(grossAmount || 0),
      };
      setResult(await api.eligibilityEvaluate(payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : "ELIGIBILITY_REQUEST_FAILED");
    } finally {
      setLoading(false);
    }
  }

  return <section className="page-stack">
    <div className="page-header">
      <div>
        <p className="eyebrow">Phase 42 · Multi-payer financing</p>
        <h1>Universal eligibility engine</h1>
        <p className="muted">Evaluate verified coverage and benefit rules without making any single payer the platform boundary.</p>
      </div>
    </div>

    {error && <div className="error-banner">{error}</div>}

    <div className="card">
      <div className="card-header">
        <div><p className="eyebrow">Eligibility decision</p><h2>Coverage + benefit evaluation</h2></div>
        <span className="status-badge">PAYER AGNOSTIC</span>
      </div>
      <div className="form-grid">
        <label>Person ID<input value={personId} onChange={e => setPersonId(e.target.value)} placeholder="UUID" /></label>
        <label>Payer ID <span className="muted small">(optional)</span><input value={payerId} onChange={e => setPayerId(e.target.value)} placeholder="UUID" /></label>
        <label>Payer plan ID <span className="muted small">(optional)</span><input value={payerPlanId} onChange={e => setPayerPlanId(e.target.value)} placeholder="UUID" /></label>
        <label>Service code <span className="muted small">(optional)</span><input value={serviceCode} onChange={e => setServiceCode(e.target.value)} placeholder="e.g. OPD-CONSULT" /></label>
        <label>Service type <span className="muted small">(optional)</span><input value={serviceType} onChange={e => setServiceType(e.target.value)} placeholder="e.g. OUTPATIENT" /></label>
        <label>Gross amount<input type="number" min="0" step="0.01" value={grossAmount} onChange={e => setGrossAmount(e.target.value)} /></label>
      </div>
      <div className="form-actions"><button type="button" className="primary" onClick={() => void evaluate()} disabled={loading || !personId.trim()}>{loading ? "Evaluating…" : "Evaluate eligibility"}</button></div>
    </div>

    {result && <div className="card">
      <div className="card-header"><div><p className="eyebrow">Decision</p><h2>{result.decision}</h2></div><span className="status-badge">{result.reason_code}</span></div>
      <div className="stat-grid">
        <div className="stat-card"><span>Payer estimate</span><strong>{result.estimated_payer_amount ?? 0}</strong><small>Estimated financing amount</small></div>
        <div className="stat-card"><span>Patient estimate</span><strong>{result.estimated_patient_amount ?? 0}</strong><small>Estimated patient amount</small></div>
        <div className="stat-card"><span>Coverage</span><strong>{result.coverage_id ? "MATCHED" : "NONE"}</strong><small>Verified active coverage</small></div>
        <div className="stat-card"><span>Payer</span><strong>{result.payer_id ? "RESOLVED" : "UNRESOLVED"}</strong><small>Financing participant</small></div>
      </div>
      <div className="notice-box"><strong>Evidence</strong><span>{JSON.stringify(result.evidence || {})}</span></div>
    </div>}

    <div className="card">
      <p className="eyebrow">Strategic role</p>
      <h2>One eligibility contract across many payers</h2>
      <p className="muted">This engine is the layer that lets facilities ask one question—“is this person covered for this service, and what financing applies?”—while the underlying payer can be SHA, private insurance, an employer scheme or another financing participant.</p>
    </div>
  </section>;
}
