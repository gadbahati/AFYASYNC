import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";

type Claim = {
  id: string;
  claim_id: string;
  invoice_id: string;
  payer_id?: string;
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

type Preflight = {
  invoice_id: string;
  ready: boolean;
  errors: string[];
  warnings: string[];
  payer_amount: number;
  patient_amount: number;
  item_count: number;
};

const money = (n: number | string) =>
  `KES ${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const STATUS_FILTERS = [
  "ALL",
  "DRAFT",
  "READY",
  "SUBMITTED",
  "PROCESSING",
  "APPROVED",
  "PARTIALLY_APPROVED",
  "REJECTED",
  "PAID",
] as const;

export function ClaimsPage() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [rejections, setRejections] = useState<RejectionItem[]>([]);
  const [invoiceId, setInvoiceId] = useState("");
  const [preflight, setPreflight] = useState<Preflight | null>(null);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUS_FILTERS)[number]>("ALL");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [responseClaim, setResponseClaim] = useState<Claim | null>(null);
  const [response, setResponse] = useState({
    status: "APPROVED" as "APPROVED" | "REJECTED" | "PARTIALLY_APPROVED",
    code: "",
    message: "",
    reference: "",
    approved: "",
  });
  const [reconcileClaim, setReconcileClaim] = useState<Claim | null>(null);
  const [receivedAmount, setReceivedAmount] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [c, r] = await Promise.all([api.listClaims(), api.listClaimRejections()]);
      setClaims(Array.isArray(c) ? c : []);
      setRejections(Array.isArray(r) ? r : []);
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "CLAIMS_LOAD_FAILED");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const filtered = useMemo(() => {
    if (statusFilter === "ALL") return claims;
    return claims.filter((c) => c.status === statusFilter);
  }, [claims, statusFilter]);

  const stats = useMemo(() => {
    const by = (s: string) => claims.filter((c) => c.status === s).length;
    const totalClaimed = claims.reduce((sum, c) => sum + Number(c.claim_amount || 0), 0);
    const totalApproved = claims.reduce((sum, c) => sum + Number(c.approved_amount || 0), 0);
    const totalPaid = claims.reduce((sum, c) => sum + Number(c.paid_amount || 0), 0);
    return {
      total: claims.length,
      rejected: by("REJECTED"),
      submitted: by("SUBMITTED") + by("PROCESSING"),
      approved: by("APPROVED") + by("PARTIALLY_APPROVED"),
      totalClaimed,
      totalApproved,
      totalPaid,
    };
  }, [claims]);

  async function runPreflight() {
    const id = invoiceId.trim();
    if (!id) return;
    setBusy(true);
    setError(null);
    setPreflight(null);
    try {
      const result = await api.claimPreflight(id);
      setPreflight(result);
      if (result.ready) {
        setMessage("Preflight passed — invoice is ready for claim creation.");
      } else {
        setMessage(null);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "PREFLIGHT_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.createClaim(invoiceId.trim());
      setInvoiceId("");
      setPreflight(null);
      setMessage("Claim created from the invoice.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "CLAIM_CREATE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function action(fn: () => Promise<unknown>, ok: string) {
    setBusy(true);
    setError(null);
    try {
      const r = (await fn()) as { message?: string } | undefined;
      setMessage(r?.message || ok);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "CLAIM_ACTION_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onResponse(e: FormEvent) {
    e.preventDefault();
    if (!responseClaim) return;
    setBusy(true);
    setError(null);
    try {
      await api.recordClaimResponse(responseClaim.id, {
        status: response.status,
        response_code: response.code.trim(),
        response_message: response.message.trim(),
        external_reference: response.reference.trim(),
        approved_amount: response.status === "REJECTED" ? 0 : Number(response.approved || 0),
      });
      setMessage("Payer response recorded.");
      setResponseClaim(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "PAYER_RESPONSE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function onReconcile(e: FormEvent) {
    e.preventDefault();
    if (!reconcileClaim) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.reconcileClaim(reconcileClaim.id, Number(receivedAmount));
      setMessage(`Reconciliation ${r.status || "recorded"}.`);
      setReconcileClaim(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "RECONCILIATION_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Revenue & financing</p>
          <h1>Claims & rework</h1>
          <p className="muted">
            SHA / payer claims from real invoices — preflight, validate, submit, response, and
            reconciliation.
          </p>
        </div>
        <button type="button" className="button secondary" onClick={() => void load()}>
          Refresh
        </button>
      </header>

      {error && <div className="error">{error}</div>}
      {message && <div className="success-box">{message}</div>}

      <div className="stats-row">
        <div className="stat-card">
          <span className="muted small">Total claims</span>
          <strong>{stats.total}</strong>
        </div>
        <div className="stat-card">
          <span className="muted small">In flight</span>
          <strong>{stats.submitted}</strong>
        </div>
        <div className="stat-card">
          <span className="muted small">Approved</span>
          <strong>{stats.approved}</strong>
        </div>
        <div className="stat-card">
          <span className="muted small">Rejected</span>
          <strong>{stats.rejected}</strong>
        </div>
        <div className="stat-card">
          <span className="muted small">Claimed</span>
          <strong>{money(stats.totalClaimed)}</strong>
        </div>
        <div className="stat-card">
          <span className="muted small">Paid</span>
          <strong>{money(stats.totalPaid)}</strong>
        </div>
      </div>

      <article className="card">
        <h2>Create claim from invoice</h2>
        <p className="muted small">
          Run <strong>preflight</strong> first to catch coverage and item issues before creating a
          claim.
        </p>
        <form className="form-grid" onSubmit={onCreate}>
          <label className="span-2">
            Invoice ID
            <input
              required
              value={invoiceId}
              onChange={(e) => {
                setInvoiceId(e.target.value);
                setPreflight(null);
              }}
              placeholder="Invoice UUID from billing"
            />
          </label>
          <div className="form-actions span-2">
            <button type="button" className="secondary" disabled={busy || !invoiceId.trim()} onClick={() => void runPreflight()}>
              Run preflight
            </button>
            <button type="submit" disabled={busy || (preflight != null && !preflight.ready)}>
              Create claim
            </button>
          </div>
        </form>
        {preflight && (
          <div className={preflight.ready ? "success-box" : "error"} style={{ marginTop: "1rem" }}>
            <strong>{preflight.ready ? "Ready for claim" : "Not ready"}</strong>
            <p className="small" style={{ margin: "0.35rem 0 0" }}>
              Items: {preflight.item_count} · Payer: {money(preflight.payer_amount)} · Patient:{" "}
              {money(preflight.patient_amount)}
            </p>
            {preflight.errors?.length > 0 && (
              <ul className="small" style={{ marginTop: "0.5rem" }}>
                {preflight.errors.map((err) => (
                  <li key={err}>{err}</li>
                ))}
              </ul>
            )}
            {preflight.warnings?.length > 0 && (
              <ul className="small muted" style={{ marginTop: "0.35rem" }}>
                {preflight.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </article>

      {loading ? (
        <p className="muted">Loading claims…</p>
      ) : (
        <>
          <article className="card">
            <div className="page-heading" style={{ marginBottom: "0.75rem" }}>
              <h2>Facility claims ({filtered.length})</h2>
              <div className="filter-chips">
                {STATUS_FILTERS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={statusFilter === s ? "chip active" : "chip"}
                    onClick={() => setStatusFilter(s)}
                  >
                    {s === "ALL" ? "All" : s.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </div>
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
                  {filtered.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <strong>{c.claim_id}</strong>
                      </td>
                      <td className="mono small">{c.invoice_id.slice(0, 8)}…</td>
                      <td>{money(c.claim_amount)}</td>
                      <td>{money(c.approved_amount)}</td>
                      <td>{money(c.paid_amount)}</td>
                      <td>
                        <span className="status-pill">{c.status}</span>
                      </td>
                      <td>
                        <div className="actions">
                          <button
                            type="button"
                            className="secondary"
                            disabled={busy}
                            onClick={() =>
                              void action(() => api.validateClaim(c.id), "Claim validated.")
                            }
                          >
                            Validate
                          </button>
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              void action(() => api.submitClaim(c.id), "Claim submitted.")
                            }
                          >
                            Submit
                          </button>
                          {["SUBMITTED", "PROCESSING"].includes(c.status) && (
                            <button
                              type="button"
                              className="secondary"
                              disabled={busy}
                              onClick={() => setResponseClaim(c)}
                            >
                              Payer response
                            </button>
                          )}
                          {["APPROVED", "PARTIALLY_APPROVED", "PAID"].includes(c.status) && (
                            <button
                              type="button"
                              className="secondary"
                              disabled={busy}
                              onClick={() => {
                                setReconcileClaim(c);
                                setReceivedAmount(
                                  String(Number(c.approved_amount) - Number(c.paid_amount)),
                                );
                              }}
                            >
                              Reconcile
                            </button>
                          )}
                          {c.status === "SUBMITTED" && (
                            <button
                              type="button"
                              className="secondary"
                              disabled={busy}
                              onClick={() =>
                                void action(
                                  () => api.sandboxRejectClaim?.(c.id) ?? api.recordClaimResponse(c.id, {
                                    status: "REJECTED",
                                    response_code: "COV001",
                                    response_message: "Coverage not verified (sandbox)",
                                    external_reference: `SANDBOX-${c.claim_id}`,
                                    approved_amount: 0,
                                  }),
                                  "Sandbox rejection recorded.",
                                )
                              }
                            >
                              Sandbox reject
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {filtered.length === 0 && (
                    <tr>
                      <td colSpan={7} className="muted">
                        No claims in this filter.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>

          <article className="card">
            <h2>Rejection workbench ({rejections.length})</h2>
            <p className="muted small">
              Each rejection includes a fix guide so staff can rework and resubmit quickly.
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Claim</th>
                    <th>Code</th>
                    <th>Problem</th>
                    <th>How to fix</th>
                    <th>Owner</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {rejections.map((r) => (
                    <tr key={r.claim_id}>
                      <td>
                        <strong>{r.claim_number}</strong>
                      </td>
                      <td>
                        <span className="status-pill">{r.guide_code}</span>
                      </td>
                      <td>
                        <strong>{r.guide_title}</strong>
                        <br />
                        <small className="muted">{r.response_message || "—"}</small>
                      </td>
                      <td>{r.guide_fix}</td>
                      <td>{r.guide_owner}</td>
                      <td>{money(r.claim_amount)}</td>
                    </tr>
                  ))}
                  {rejections.length === 0 && (
                    <tr>
                      <td colSpan={6} className="muted">
                        No rejected claims — good standing.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>
        </>
      )}

      {responseClaim && (
        <div className="modal-backdrop">
          <article className="card modal-card">
            <div className="page-heading">
              <div>
                <p className="eyebrow">Payer response</p>
                <h2>{responseClaim.claim_id}</h2>
              </div>
              <button type="button" className="secondary" onClick={() => setResponseClaim(null)}>
                Close
              </button>
            </div>
            <form className="form-grid" onSubmit={onResponse}>
              <label>
                Status
                <select
                  value={response.status}
                  onChange={(e) =>
                    setResponse({
                      ...response,
                      status: e.target.value as typeof response.status,
                    })
                  }
                >
                  <option value="APPROVED">APPROVED</option>
                  <option value="PARTIALLY_APPROVED">PARTIALLY_APPROVED</option>
                  <option value="REJECTED">REJECTED</option>
                </select>
              </label>
              <label>
                Response code
                <input
                  required
                  value={response.code}
                  onChange={(e) => setResponse({ ...response, code: e.target.value })}
                />
              </label>
              <label className="span-2">
                Response message
                <input
                  required
                  value={response.message}
                  onChange={(e) => setResponse({ ...response, message: e.target.value })}
                />
              </label>
              <label>
                External reference
                <input
                  required
                  value={response.reference}
                  onChange={(e) => setResponse({ ...response, reference: e.target.value })}
                />
              </label>
              {response.status !== "REJECTED" && (
                <label>
                  Approved amount (KES)
                  <input
                    required
                    type="number"
                    min="0"
                    step="0.01"
                    value={response.approved}
                    onChange={(e) => setResponse({ ...response, approved: e.target.value })}
                  />
                </label>
              )}
              <div className="form-actions span-2">
                <button type="submit" disabled={busy}>
                  Record payer response
                </button>
              </div>
            </form>
          </article>
        </div>
      )}

      {reconcileClaim && (
        <div className="modal-backdrop">
          <article className="card modal-card">
            <div className="page-heading">
              <div>
                <p className="eyebrow">Payment reconciliation</p>
                <h2>{reconcileClaim.claim_id}</h2>
              </div>
              <button type="button" className="secondary" onClick={() => setReconcileClaim(null)}>
                Close
              </button>
            </div>
            <form className="form-grid" onSubmit={onReconcile}>
              <label className="span-2">
                Amount received (KES)
                <input
                  required
                  type="number"
                  min="0"
                  step="0.01"
                  value={receivedAmount}
                  onChange={(e) => setReceivedAmount(e.target.value)}
                />
              </label>
              <div className="form-actions span-2">
                <button type="submit" disabled={busy}>
                  Record reconciliation
                </button>
              </div>
            </form>
          </article>
        </div>
      )}
    </section>
  );
}
