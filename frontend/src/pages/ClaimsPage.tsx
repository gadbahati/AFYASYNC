import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";

type Claim = { id: string; claim_id: string; invoice_id: string; payer_id: string; claim_amount: number | string; approved_amount: number | string; paid_amount: number | string; status: string };
type RejectionItem = { claim_id: string; claim_number: string; invoice_id: string; status: string; claim_amount: number; response_code: string | null; response_message: string | null; guide_code: string; guide_title: string; guide_fix: string; guide_owner: string };
const money = (n: number | string) => `KES ${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function ClaimsPage() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [rejections, setRejections] = useState<RejectionItem[]>([]);
  const [invoiceId, setInvoiceId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [responseClaim, setResponseClaim] = useState<Claim | null>(null);
  const [response, setResponse] = useState({ status: "APPROVED" as "APPROVED" | "REJECTED" | "PARTIALLY_APPROVED", code: "", message: "", reference: "", approved: "" });
  const [reconcileClaim, setReconcileClaim] = useState<Claim | null>(null);
  const [receivedAmount, setReceivedAmount] = useState("");

  const selectedBalance = useMemo(() => responseClaim ? Math.max(Number(responseClaim.claim_amount) - Number(responseClaim.paid_amount), 0) : 0, [responseClaim]);

  function load() {
    setLoading(true); setError(null);
    Promise.all([api.listClaims(), api.listClaimRejections()]).then(([c, r]) => { setClaims(c); setRejections(r); }).catch((e) => setError(e instanceof ApiError ? e.code : "CLAIMS_LOAD_FAILED")).finally(() => setLoading(false));
  }
  useEffect(() => { load(); }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError(null); setMessage(null);
    try { await api.createClaim(invoiceId.trim()); setInvoiceId(""); setMessage("Claim created"); load(); } catch (err) { setError(err instanceof ApiError ? err.code : "CLAIM_CREATE_FAILED"); } finally { setBusy(false); }
  }
  async function onValidate(id: string) { setBusy(true); setError(null); try { const res = await api.validateClaim(id); setMessage(res.valid ? "Claim validated and ready" : `Validation errors: ${res.errors.join(", ")}`); load(); } catch (err) { setError(err instanceof ApiError ? err.code : "VALIDATE_FAILED"); } finally { setBusy(false); } }
  async function onSubmit(id: string) { setBusy(true); setError(null); try { const res = await api.submitClaim(id); setMessage(res.message || `Submitted: ${res.status}`); load(); } catch (err) { setError(err instanceof ApiError ? err.code : "SUBMIT_FAILED"); } finally { setBusy(false); } }
  async function onResubmit(id: string) { setBusy(true); setError(null); setMessage(null); try { const res = await api.resubmitClaim(id); setMessage(res.message || `Re-submitted: ${res.status}`); load(); } catch (err) { setError(err instanceof ApiError ? err.code : "RESUBMIT_FAILED"); } finally { setBusy(false); } }

  async function onResponse(e: FormEvent) {
    e.preventDefault(); if (!responseClaim) return; setBusy(true); setError(null); setMessage(null);
    try {
      await api.recordClaimResponse(responseClaim.id, { status: response.status, response_code: response.code.trim(), response_message: response.message.trim(), external_reference: response.reference.trim(), approved_amount: response.status === "REJECTED" ? 0 : Number(response.approved || 0) });
      setMessage("Payer response recorded"); setResponseClaim(null); setResponse({ status: "APPROVED", code: "", message: "", reference: "", approved: "" }); load();
    } catch (err) { setError(err instanceof ApiError ? err.code : "PAYER_RESPONSE_FAILED"); } finally { setBusy(false); }
  }
  async function onReconcile(e: FormEvent) {
    e.preventDefault(); if (!reconcileClaim) return; setBusy(true); setError(null); setMessage(null);
    try { const result = await api.reconcileClaim(reconcileClaim.id, Number(receivedAmount)); setMessage(`Reconciliation ${result.status || "recorded"}: ${money(result.difference || 0)} difference`); setReconcileClaim(null); setReceivedAmount(""); load(); } catch (err) { setError(err instanceof ApiError ? err.code : "RECONCILIATION_FAILED"); } finally { setBusy(false); }
  }

  return (
    <section className="page-stack">
      <header className="page-heading"><div><p className="eyebrow">Revenue & financing</p><h1>Claims & rework</h1><p className="muted">Move payer claims from creation through validation, submission, response and payment reconciliation.</p></div><button type="button" className="button secondary" onClick={load}>Refresh</button></header>
      {error && <div className="error">{error}</div>}{message && <div className="success-box">{message}</div>}

      <article className="card"><h2>Create claim from invoice</h2><form className="form-grid" onSubmit={onCreate}><label className="full">Invoice ID<input required value={invoiceId} onChange={(e) => setInvoiceId(e.target.value)} placeholder="Invoice UUID" /></label><div className="full actions"><button type="submit" disabled={busy}>{busy ? "Creating…" : "Create claim"}</button></div></form></article>

      {loading ? <p>Loading claims…</p> : <>
        <article className="card"><h2>Facility claims ({claims.length})</h2><div className="table-wrap"><table><thead><tr><th>Claim</th><th>Invoice</th><th>Amount</th><th>Approved</th><th>Paid</th><th>Status</th><th>Actions</th></tr></thead><tbody>
          {claims.map((c) => <tr key={c.id}><td>{c.claim_id}</td><td>{c.invoice_id}</td><td>{money(c.claim_amount)}</td><td>{money(c.approved_amount)}</td><td>{money(c.paid_amount)}</td><td><span className="status-pill">{c.status}</span></td><td><div className="form-actions">
            <button type="button" className="button secondary" disabled={busy} onClick={() => onValidate(c.id)}>Validate</button>
            <button type="button" disabled={busy} onClick={() => onSubmit(c.id)}>Submit</button>
            {c.status === "REJECTED" && <button type="button" className="button secondary" disabled={busy} onClick={() => onResubmit(c.id)}>Validate & resubmit</button>}
            {(c.status === "SUBMITTED" || c.status === "PROCESSING") && <button type="button" className="button secondary" disabled={busy} onClick={() => { setResponseClaim(c); setResponse({ status: "APPROVED", code: "", message: "", reference: "", approved: "" }); }}>Payer response</button>}
            {(["APPROVED", "PARTIALLY_APPROVED", "PAID"].includes(c.status)) && <button type="button" className="button secondary" disabled={busy} onClick={() => { setReconcileClaim(c); setReceivedAmount(String(Number(c.approved_amount) - Number(c.paid_amount))); }}>Reconcile</button>}
          </div></td></tr>)}
          {claims.length === 0 && <tr><td colSpan={7} className="muted">No claims yet for this facility.</td></tr>}
        </tbody></table></div></article>

        <article className="card"><h2>Rejection workbench ({rejections.length})</h2><p className="muted">Rejected claims are mapped to an actionable fix and responsible owner. After the correction is made, re-validation and resubmission use the normal payer workflow.</p><div className="table-wrap"><table><thead><tr><th>Claim</th><th>Code</th><th>Problem</th><th>Fix</th><th>Owner</th><th>Amount</th></tr></thead><tbody>
          {rejections.map((r) => <tr key={r.claim_id}><td>{r.claim_number}</td><td>{r.guide_code}</td><td><strong>{r.guide_title}</strong><br /><small>{r.response_message || "—"}</small></td><td>{r.guide_fix}</td><td>{r.guide_owner}</td><td>{money(r.claim_amount)}</td></tr>)}
          {rejections.length === 0 && <tr><td colSpan={6} className="muted">No rejected claims.</td></tr>}
        </tbody></table></div></article>
      </>}

      {responseClaim && <div className="modal-backdrop"><article className="card modal-card"><div className="page-heading"><div><p className="eyebrow">Payer response</p><h2>{responseClaim.claim_id}</h2><p className="muted">Claim amount {money(responseClaim.claim_amount)} · current unpaid balance {money(selectedBalance)}</p></div><button type="button" className="button secondary" onClick={() => setResponseClaim(null)}>Close</button></div><form className="form-grid" onSubmit={onResponse}>
        <label>Status<select value={response.status} onChange={(e) => setResponse({ ...response, status: e.target.value as typeof response.status })}><option value="APPROVED">Approved</option><option value="PARTIALLY_APPROVED">Partially approved</option><option value="REJECTED">Rejected</option></select></label>
        <label>Response code<input required maxLength={80} value={response.code} onChange={(e) => setResponse({ ...response, code: e.target.value })} /></label>
        <label className="full">Response message<input required maxLength={500} value={response.message} onChange={(e) => setResponse({ ...response, message: e.target.value })} /></label>
        <label>External reference<input required maxLength={150} value={response.reference} onChange={(e) => setResponse({ ...response, reference: e.target.value })} /></label>
        {response.status !== "REJECTED" && <label>Approved amount<input required type="number" min="0" step="0.01" value={response.approved} onChange={(e) => setResponse({ ...response, approved: e.target.value })} /></label>}
        <div className="full actions"><button type="submit" disabled={busy}>{busy ? "Recording…" : "Record payer response"}</button></div>
      </form></article></div>}

      {reconcileClaim && <div className="modal-backdrop"><article className="card modal-card"><div className="page-heading"><div><p className="eyebrow">Payment reconciliation</p><h2>{reconcileClaim.claim_id}</h2><p className="muted">Expected approved amount: {money(reconcileClaim.approved_amount)}</p></div><button type="button" className="button secondary" onClick={() => setReconcileClaim(null)}>Close</button></div><form className="form-grid" onSubmit={onReconcile}><label className="full">Amount actually received (KES)<input required type="number" min="0" step="0.01" value={receivedAmount} onChange={(e) => setReceivedAmount(e.target.value)} /></label><div className="full actions"><button type="submit" disabled={busy}>{busy ? "Reconciling…" : "Record reconciliation"}</button></div></form></article></div>}
    </section>
  );
}
