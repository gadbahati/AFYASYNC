import type { FormEvent } from "react";
import { api } from "../api/client";

/** Claims list, filters, actions, rejection guide, response & reconcile forms. Phase 110. */
export function ClaimsClaimsTable(props: any) {
  const {
    loading,
    scope,
    filtered,
    statusFilter,
    setStatusFilter,
    statusFilters,
    busy,
    action,
    canValidate,
    canSubmit,
    canRespond,
    canReconcile,
    canSandboxReject,
    setResponseClaim,
    setResponse,
    setReconcileClaim,
    setReceivedAmount,
    responseClaim,
    response,
    onResponse,
    reconcileClaim,
    receivedAmount,
    onReconcile,
    rejections,
    money,
  } = props;
  if (loading) return <p className="muted">Loading claims…</p>;
  const STATUS_FILTERS = statusFilters;

  return (
    <>
      <article className="card">
        <div className="page-heading" style={{ marginBottom: "0.75rem" }}>
          <h2>
            Claims ({scope}) — {filtered.length}
          </h2>
          <div className="filter-chips">
            {STATUS_FILTERS.map((s: string) => (
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
              {filtered.map((c: any) => (
                <tr key={c.id}>
                  <td>
                    <strong>{c.claim_id}</strong>
                  </td>
                  <td className="mono small" title={c.invoice_id}>
                    {c.invoice_id.slice(0, 8)}…
                  </td>
                  <td>{money(c.claim_amount)}</td>
                  <td>{money(c.approved_amount)}</td>
                  <td>{money(c.paid_amount)}</td>
                  <td>
                    <span className="status-pill">{c.status}</span>
                  </td>
                  <td>
                    <div className="actions">
                      {canValidate(c.status) && (
                        <button
                          type="button"
                          className="secondary"
                          disabled={busy}
                          onClick={() => void action(() => api.validateClaim(c.id), "Claim validated.")}
                        >
                          Validate
                        </button>
                      )}
                      {canSubmit(c.status) && (
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => void action(() => api.submitClaim(c.id), "Claim submitted.")}
                        >
                          Submit
                        </button>
                      )}
                      {canRespond(c.status) && (
                        <button
                          type="button"
                          className="secondary"
                          disabled={busy}
                          onClick={() => {
                            setResponseClaim(c);
                            setResponse({
                              status: "ACCEPTED",
                              code: "",
                              message: "",
                              reference: "",
                              approved: String(c.claim_amount),
                            });
                          }}
                        >
                          Payer response
                        </button>
                      )}
                      {canReconcile(c.status) && (
                        <button
                          type="button"
                          className="secondary"
                          disabled={busy}
                          onClick={() => {
                            setReconcileClaim(c);
                            setReceivedAmount(
                              String(Math.max(0, Number(c.approved_amount) - Number(c.paid_amount))),
                            );
                          }}
                        >
                          Reconcile
                        </button>
                      )}
                      {canSandboxReject(c.status) && (
                        <button
                          type="button"
                          className="secondary"
                          disabled={busy}
                          onClick={() =>
                            void action(() => api.sandboxRejectClaim(c.id), "Sandbox rejection recorded.")
                          }
                        >
                          Sandbox reject
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      {rejections && rejections.length > 0 && (
        <article className="card">
          <h2>Rejection workbench</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Claim</th>
                  <th>Code</th>
                  <th>Guide</th>
                  <th>Owner</th>
                </tr>
              </thead>
              <tbody>
                {rejections.map((r: any) => (
                  <tr key={r.claim_id}>
                    <td>{r.claim_number}</td>
                    <td>{r.response_code || "—"}</td>
                    <td>
                      <strong>{r.guide_title}</strong>
                      <p className="muted small">{r.guide_fix}</p>
                    </td>
                    <td>{r.guide_owner}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      )}

      {responseClaim && (
        <article className="card">
          <h2>Payer response — {responseClaim.claim_id}</h2>
          <form className="form-grid" onSubmit={onResponse}>
            <label>
              Status
              <select
                value={response.status}
                onChange={(e) => setResponse((s: any) => ({ ...s, status: e.target.value }))}
              >
                <option value="ACCEPTED">ACCEPTED</option>
                <option value="UNDER_REVIEW">UNDER_REVIEW</option>
                <option value="REJECTED">REJECTED</option>
                <option value="PARTIALLY_PAID">PARTIALLY_PAID</option>
                <option value="PAID">PAID</option>
              </select>
            </label>
            <label>
              Code
              <input
                required
                value={response.code}
                onChange={(e) => setResponse((s: any) => ({ ...s, code: e.target.value }))}
                maxLength={80}
              />
            </label>
            <label className="span-2">
              Message
              <input
                required
                value={response.message}
                onChange={(e) => setResponse((s: any) => ({ ...s, message: e.target.value }))}
                maxLength={500}
              />
            </label>
            <label>
              External reference
              <input
                required
                value={response.reference}
                onChange={(e) => setResponse((s: any) => ({ ...s, reference: e.target.value }))}
                maxLength={150}
              />
            </label>
            <label>
              Approved amount
              <input
                value={response.approved}
                onChange={(e) => setResponse((s: any) => ({ ...s, approved: e.target.value }))}
                disabled={response.status === "REJECTED"}
              />
            </label>
            <div className="form-actions span-2">
              <button type="button" className="secondary" onClick={() => setResponseClaim(null)}>
                Cancel
              </button>
              <button type="submit" disabled={busy}>
                Save response
              </button>
            </div>
          </form>
        </article>
      )}

      {reconcileClaim && (
        <article className="card">
          <h2>Reconcile — {reconcileClaim.claim_id}</h2>
          <form className="form-grid" onSubmit={onReconcile}>
            <label>
              Received amount (KES)
              <input
                required
                value={receivedAmount}
                onChange={(e) => setReceivedAmount(e.target.value)}
              />
            </label>
            <div className="form-actions span-2">
              <button type="button" className="secondary" onClick={() => setReconcileClaim(null)}>
                Cancel
              </button>
              <button type="submit" disabled={busy}>
                Reconcile
              </button>
            </div>
          </form>
        </article>
      )}

      <p className="muted small">Developed by BAHATI GAD WANGWE · Phase 110 claims workbench</p>
    </>
  );
}

// silence unused FormEvent import for type-only consumers
type _FormEvent = FormEvent;
