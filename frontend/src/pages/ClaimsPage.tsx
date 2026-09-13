import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";

type Claim = {
  id: string;
  claim_id: string;
  invoice_id: string;
  payer_id: string;
  claim_amount: number | string;
  approved_amount: number | string;
  paid_amount: number | string;
  status: string;
};

type RejectionItem = {
  claim_id: string;
  claim_number: string;
  invoice_id: string;
  status: string;
  claim_amount: number;
  response_code: string | null;
  response_message: string | null;
  guide_code: string;
  guide_title: string;
  guide_fix: string;
  guide_owner: string;
};

const money = (n: number | string) => `KES ${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export function ClaimsPage() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [rejections, setRejections] = useState<RejectionItem[]>([]);
  const [invoiceId, setInvoiceId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    Promise.all([
      api.listClaims().catch(() => [] as Claim[]),
      api.listClaimRejections().catch(() => [] as RejectionItem[]),
    ])
      .then(([c, r]) => {
        setClaims(c);
        setRejections(r);
      })
      .catch((e) => setError(e instanceof ApiError ? e.code : "CLAIMS_LOAD_FAILED"))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.createClaim(invoiceId.trim());
      setInvoiceId("");
      setMessage("Claim created");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "CLAIM_CREATE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onValidate(id: string) {
    setBusy(true);
    setError(null);
    try {
      const res = await api.validateClaim(id);
      setMessage(res.valid ? "Claim valid / READY" : `Validation errors: ${res.errors.join(", ")}`);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "VALIDATE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(id: string) {
    setBusy(true);
    setError(null);
    try {
      const res = await api.submitClaim(id);
      setMessage(res.message || `Submitted: ${res.status}`);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "SUBMIT_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onSandboxReject(id: string) {
    setBusy(true);
    setError(null);
    try {
      await api.sandboxRejectClaim(id, { response_code: "COV001", response_message: "Coverage not verified (sandbox)" });
      setMessage("Sandbox rejection recorded — see workbench for fix guidance");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "SANDBOX_REJECT_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Payer workflow</p>
          <h1>Claims</h1>
          <p className="muted">
            Create · validate · submit. Rejection workbench maps codes to fixes (works before live SHA API exists).
          </p>
        </div>
        <button type="button" className="button secondary" onClick={load}>Refresh</button>
      </header>
      {error && <div className="error">{error}</div>}
      {message && <div className="success-box">{message}</div>}
      <article className="card">
        <h2>Create claim from invoice</h2>
        <form className="form-grid" onSubmit={onCreate}>
          <label className="full">Invoice ID
            <input required value={invoiceId} onChange={(e) => setInvoiceId(e.target.value)} placeholder="Invoice UUID" />
          </label>
          <div className="full actions"><button type="submit" disabled={busy}>{busy ? "Creating…" : "Create claim"}</button></div>
        </form>
      </article>
      {loading ? <p>Loading claims…</p> : (
        <>
          <article className="card">
            <h2>Facility claims ({claims.length})</h2>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Claim</th>
                    <th>Invoice</th>
                    <th>Amount</th>
                    <th>Approved</th>
                    <th>Paid</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {claims.map((c) => (
                    <tr key={c.id}>
                      <td>{c.claim_id}</td>
                      <td>{c.invoice_id}</td>
                      <td>{money(c.claim_amount)}</td>
                      <td>{money(c.approved_amount)}</td>
                      <td>{money(c.paid_amount)}</td>
                      <td><span className="status-pill">{c.status}</span></td>
                      <td>
                        <div className="form-actions">
                          <button type="button" className="button secondary" disabled={busy} onClick={() => onValidate(c.id)}>Validate</button>
                          <button type="button" disabled={busy} onClick={() => onSubmit(c.id)}>Submit</button>
                          {(c.status === "READY" || c.status === "SUBMITTED") && (
                            <button type="button" className="button secondary" disabled={busy} onClick={() => onSandboxReject(c.id)}>Sandbox reject</button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {claims.length === 0 && (
                    <tr><td colSpan={7} className="muted">No claims yet for this facility.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>
          <article className="card">
            <h2>Rejection workbench ({rejections.length})</h2>
            <p className="muted">Every rejection shows what to fix and who owns the step — the experience SHA portals usually lack.</p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Claim</th>
                    <th>Code</th>
                    <th>Problem</th>
                    <th>Fix</th>
                    <th>Owner</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {rejections.map((r) => (
                    <tr key={r.claim_id}>
                      <td>{r.claim_number}</td>
                      <td>{r.guide_code}</td>
                      <td><strong>{r.guide_title}</strong><br /><small>{r.response_message || "—"}</small></td>
                      <td>{r.guide_fix}</td>
                      <td>{r.guide_owner}</td>
                      <td>{money(r.claim_amount)}</td>
                    </tr>
                  ))}
                  {rejections.length === 0 && (
                    <tr><td colSpan={6} className="muted">No rejected claims. Use Sandbox reject on a READY claim to train the workbench.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>
        </>
      )}
    </section>
  );
}
