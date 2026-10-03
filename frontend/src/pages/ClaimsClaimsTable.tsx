import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";

/** Claims workbench — fraud scan, appeals, adjudication, settlement. Phase 118. */
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

  const [adjDetail, setAdjDetail] = useState<any | null>(null);
  const [adjLoading, setAdjLoading] = useState(false);
  const [adjError, setAdjError] = useState("");
  const [obligationInfo, setObligationInfo] = useState<any[] | null>(null);
  const [obligationError, setObligationError] = useState("");
  const [lastObligationClaimId, setLastObligationClaimId] = useState("");

  async function loadObligation(claimId: string) {
    setObligationError("");
    setObligationInfo(null);
    setLastObligationClaimId(claimId);
    try {
      const rows = await api.settlementListObligations({ claim_id: claimId, limit: 5 });
      setObligationInfo(Array.isArray(rows) ? rows : []);
    } catch (e) {
      setObligationError(e instanceof ApiError ? e.message || e.code : "OBLIGATION_LOAD_FAILED");
    }
  }

  async function loadAdjudicationDetail(claimId: string) {
    setAdjLoading(true);
    setAdjError("");
    setAdjDetail(null);
    try {
      setAdjDetail(await api.getClaimAdjudicationLines(claimId));
    } catch (e) {
      setAdjError(e instanceof ApiError ? e.message || e.code : "ADJUDICATION_LOAD_FAILED");
    } finally {
      setAdjLoading(false);
    }
  }

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
                    {c.status === "REJECTED" && (
                      <span
                        className="status-pill"
                        style={{ marginLeft: 6, background: "#b91c1c", color: "#fff" }}
                        title="Fraud / rejection rework priority"
                      >
                        HIGH RISK
                      </span>
                    )}
                    {c.status === "UNDER_REVIEW" && (
                      <span
                        className="status-pill"
                        style={{ marginLeft: 6, background: "#b45309", color: "#fff" }}
                        title="Under review"
                      >
                        REVIEW
                      </span>
                    )}
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
                      {["DRAFT", "READY", "SUBMITTED", "UNDER_REVIEW", "REJECTED"].includes(c.status) && (
                        <button
                          type="button"
                          className="secondary"
                          disabled={busy}
                          onClick={() =>
                            void action(async () => {
                              const r = await api.adjudicateClaim(c.id, false);
                              void loadAdjudicationDetail(c.id);
                              void loadObligation(c.id);
                              return {
                                message: `Adjudicated: ${r.decision} · allowed ${r.allowed_amount}`,
                              };
                            }, "Claim adjudicated.")
                          }
                        >
                          Adjudicate
                        </button>
                      )}
                      {["ACCEPTED", "REJECTED"].includes(c.status) && (
                        <button
                          type="button"
                          className="secondary"
                          disabled={busy}
                          onClick={() =>
                            void action(async () => {
                              const r = await api.adjudicateClaim(c.id, true);
                              void loadAdjudicationDetail(c.id);
                              void loadObligation(c.id);
                              return {
                                message: `Re-adjudicated: ${r.decision} · allowed ${r.allowed_amount}`,
                              };
                            }, "Claim re-adjudicated.")
                          }
                        >
                          Re-adjudicate
                        </button>
                      )}
                      <button
                        type="button"
                        className="secondary"
                        disabled={adjLoading}
                        onClick={() => void loadAdjudicationDetail(c.id)}
                      >
                        Adj. detail
                      </button>
                      <button type="button" className="secondary" onClick={() => void loadObligation(c.id)}>
                        Obligation
                      </button>
                      <Link
                        to={`/settlements?claim_id=${encodeURIComponent(c.id)}`}
                        className="secondary"
                        style={{ display: "inline-block", padding: "0.35rem 0.6rem", textDecoration: "none" }}
                      >
                        Settle
                      </Link>
                      <button
                        type="button"
                        className="secondary"
                        disabled={busy}
                        onClick={() =>
                          void action(async () => {
                            const r = await api.fraudScanClaim(c.id);
                            return {
                              message: `Fraud scan: ${r.band} (${r.score}/100)${(r.flags || [])
                                .map((f: any) => ` · ${f.code}`)
                                .join("")}`,
                            };
                          }, "Fraud scan complete.")
                        }
                      >
                        Fraud scan
                      </button>
                      {c.status === "REJECTED" && (
                        <button
                          type="button"
                          className="secondary"
                          disabled={busy}
                          onClick={() => {
                            const reason = window.prompt(
                              "Appeal reason (min 10 characters — clinical justification):",
                            );
                            if (!reason || reason.trim().length < 10) return;
                            void action(
                              () => api.appealClaim(c.id, { reason: reason.trim() }),
                              "Appeal submitted — claim under review.",
                            );
                          }}
                        >
                          Appeal
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

      {(adjDetail || adjError || adjLoading) && (
        <article className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ margin: 0 }}>Adjudication detail</h2>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setAdjDetail(null);
                setAdjError("");
              }}
            >
              Close
            </button>
          </div>
          {adjLoading && <p className="muted">Loading…</p>}
          {adjError && <div className="error">{adjError}</div>}
          {adjDetail && !adjDetail.decision && (
            <p className="muted">No adjudication yet. Run Adjudicate first.</p>
          )}
          {adjDetail?.decision && (
            <>
              <p className="small">
                <strong>{adjDetail.decision}</strong> · allowed {money(adjDetail.allowed_amount)} · patient{" "}
                {money(adjDetail.patient_amount)} · {adjDetail.reason_code}
              </p>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Submitted</th>
                      <th>Allowed</th>
                      <th>Decision</th>
                      <th>Reason</th>
                      <th>Service</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(adjDetail.lines || []).map((ln: any) => (
                      <tr key={ln.id}>
                        <td>{money(ln.submitted_amount)}</td>
                        <td>{money(ln.allowed_amount)}</td>
                        <td>{ln.decision}</td>
                        <td>{ln.reason_code}</td>
                        <td>{ln.evidence?.service_code || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </article>
      )}

      {(obligationInfo || obligationError) && (
        <article className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ margin: 0 }}>Settlement obligation</h2>
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setObligationInfo(null);
                setObligationError("");
              }}
            >
              Close
            </button>
          </div>
          {obligationError && <div className="error">{obligationError}</div>}
          {obligationInfo && obligationInfo.length === 0 && (
            <>
              <p className="muted">No obligation for this claim yet (adjudicate a payable claim first).</p>
              {lastObligationClaimId && (
                <p>
                  <Link to={`/settlements?claim_id=${encodeURIComponent(lastObligationClaimId)}`}>
                    Open Settlement workspace with this claim →
                  </Link>
                </p>
              )}
            </>
          )}
          {obligationInfo && obligationInfo.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Number</th>
                    <th>Status</th>
                    <th>Payable</th>
                    <th>Patient</th>
                    <th>Created</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {obligationInfo.map((o: any) => (
                    <tr key={o.id}>
                      <td>{o.obligation_number}</td>
                      <td>{o.status}</td>
                      <td>{money(o.payable_amount)}</td>
                      <td>{money(o.patient_amount)}</td>
                      <td className="muted small">{o.created_at || "—"}</td>
                      <td>
                        <Link
                          to={`/settlements?claim_id=${encodeURIComponent(o.claim_id || lastObligationClaimId)}`}
                          className="secondary"
                          style={{
                            display: "inline-block",
                            padding: "0.25rem 0.5rem",
                            textDecoration: "none",
                          }}
                        >
                          Open settlement
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      )}

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
                </tr>
              </thead>
              <tbody>
                {rejections.map((r: any) => (
                  <tr key={r.claim_id}>
                    <td>{r.claim_number}</td>
                    <td>{r.response_code || "—"}</td>
                    <td>{r.guide_title}</td>
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
              />
            </label>
            <label className="span-2">
              Message
              <input
                required
                value={response.message}
                onChange={(e) => setResponse((s: any) => ({ ...s, message: e.target.value }))}
              />
            </label>
            <label>
              Reference
              <input
                required
                value={response.reference}
                onChange={(e) => setResponse((s: any) => ({ ...s, reference: e.target.value }))}
              />
            </label>
            <div className="form-actions span-2">
              <button type="button" className="secondary" onClick={() => setResponseClaim(null)}>
                Cancel
              </button>
              <button type="submit" disabled={busy}>
                Save
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
              Received amount
              <input required value={receivedAmount} onChange={(e) => setReceivedAmount(e.target.value)} />
            </label>
            <div className="form-actions">
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

      <p className="muted small">Developed by BAHATI GAD WANGWE · Phase 118</p>
    </>
  );
}