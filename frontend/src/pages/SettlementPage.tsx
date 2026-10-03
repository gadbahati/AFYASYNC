import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";

export default function SettlementPage() {
  const [searchParams] = useSearchParams();
  const [claimId, setClaimId] = useState(() => searchParams.get("claim_id") || "");
  const [payerId, setPayerId] = useState("");
  const [batchId, setBatchId] = useState("");
  const [obligationId, setObligationId] = useState("");
  const [amount, setAmount] = useState("");
  const [received, setReceived] = useState("");
  const [method, setMethod] = useState("BANK_TRANSFER");
  const [message, setMessage] = useState("");
  const [batches, setBatches] = useState<any[]>([]);
  const [obligations, setObligations] = useState<any[]>([]);
  const [overview, setOverview] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const loadBatches = useCallback(async () => {
    try {
      const rows = await api.settlementListBatches();
      setBatches(Array.isArray(rows) ? rows : []);
    } catch {
      setBatches([]);
    }
  }, []);

  const loadObligations = useCallback(async () => {
    try {
      const rows = await api.settlementListObligations({ status: "READY", limit: 50 });
      setObligations(Array.isArray(rows) ? rows : []);
    } catch {
      setObligations([]);
    }
  }, []);

  const loadOverview = useCallback(async () => {
    try {
      setOverview(await api.settlementOverview());
    } catch {
      setOverview(null);
    }
  }, []);

  useEffect(() => {
    void loadBatches();
    void loadObligations();
    void loadOverview();
  }, [loadBatches, loadObligations, loadOverview]);

  function selectObligation(o: any) {
    setObligationId(o.id);
    setClaimId(o.claim_id || "");
    setPayerId(o.payer_id || "");
    setAmount(String(o.payable_amount ?? ""));
    setMessage(`Selected obligation ${o.obligation_number} (${o.status})`);
  }

  async function run(fn: () => Promise<any>, okMsg?: string) {
    setBusy(true);
    setMessage("");
    try {
      const r = await fn();
      setMessage(okMsg ? `${okMsg}\n${JSON.stringify(r, null, 2)}` : JSON.stringify(r, null, 2));
      await loadBatches();
      await loadObligations();
      await loadOverview();
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message || e.code : e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Phase 116 · Provider settlement</p>
          <h1>Settlement & provider payments</h1>
          <p className="muted">
            Select a READY obligation to auto-fill claim, payer, and amount — then batch, pay, and reconcile.
          </p>
        </div>
      </header>

      {overview && (
        <div className="stats-row">
          <div className="stat-card">
            <span className="muted small">READY</span>
            <strong>{overview.ready_obligations}</strong>
          </div>
          <div className="stat-card">
            <span className="muted small">In batch</span>
            <strong>{overview.in_batch_obligations}</strong>
          </div>
          <div className="stat-card">
            <span className="muted small">Payments recorded</span>
            <strong>{Number(overview.provider_payments_recorded || 0).toLocaleString()}</strong>
          </div>
        </div>
      )}

      <article className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>READY obligations</h2>
          <button type="button" className="secondary" onClick={() => void loadObligations()}>
            Refresh
          </button>
        </div>
        {obligations.length === 0 && (
          <p className="muted">No READY obligations. Adjudicate a payable claim first.</p>
        )}
        {obligations.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Payable</th>
                  <th>Patient</th>
                  <th>Claim</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {obligations.map((o) => (
                  <tr key={o.id}>
                    <td>{o.obligation_number}</td>
                    <td>{o.payable_amount}</td>
                    <td>{o.patient_amount}</td>
                    <td className="mono small">{String(o.claim_id).slice(0, 8)}…</td>
                    <td>
                      <button type="button" className="secondary" onClick={() => selectObligation(o)}>
                        Use
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>

      <article className="card">
        <h2>1. Settlement obligation</h2>
        <div className="form-grid">
          <label>
            Claim ID
            <input value={claimId} onChange={(e) => setClaimId(e.target.value)} placeholder="UUID" />
          </label>
        </div>
        <div className="form-actions">
          <button
            type="button"
            disabled={busy || !claimId}
            onClick={() =>
              void run(() => api.settlementCreateObligation(claimId.trim()), "Obligation created.")
            }
          >
            Generate obligation
          </button>
        </div>
      </article>

      <article className="card">
        <h2>2. Create batch</h2>
        <div className="form-grid">
          <label>
            Payer ID
            <input value={payerId} onChange={(e) => setPayerId(e.target.value)} placeholder="UUID" />
          </label>
        </div>
        <div className="form-actions">
          <button
            type="button"
            disabled={busy || !payerId}
            onClick={() => void run(() => api.settlementCreateBatch(payerId.trim()), "Batch created.")}
          >
            Create batch
          </button>
        </div>
      </article>

      <article className="card">
        <h2>3. Record payment</h2>
        <div className="form-grid">
          <label>
            Batch ID
            <input value={batchId} onChange={(e) => setBatchId(e.target.value)} />
          </label>
          <label>
            Obligation ID
            <input value={obligationId} onChange={(e) => setObligationId(e.target.value)} />
          </label>
          <label>
            Amount
            <input type="number" min="0" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </label>
          <label>
            Method
            <select value={method} onChange={(e) => setMethod(e.target.value)}>
              <option value="BANK_TRANSFER">BANK_TRANSFER</option>
              <option value="MPESA">MPESA</option>
              <option value="CHEQUE">CHEQUE</option>
            </select>
          </label>
        </div>
        <div className="form-actions">
          <button
            type="button"
            disabled={busy || !batchId || !obligationId || !amount}
            onClick={() =>
              void run(
                () =>
                  api.settlementRecordPayment(batchId.trim(), {
                    obligation_id: obligationId.trim(),
                    amount: Number(amount),
                    method,
                  }),
                "Payment recorded.",
              )
            }
          >
            Record payment
          </button>
        </div>
      </article>

      <article className="card">
        <h2>4. Reconcile batch</h2>
        <div className="form-grid">
          <label>
            Batch ID
            <input value={batchId} onChange={(e) => setBatchId(e.target.value)} />
          </label>
          <label>
            Received amount
            <input
              type="number"
              min="0"
              step="0.01"
              value={received}
              onChange={(e) => setReceived(e.target.value)}
            />
          </label>
        </div>
        <div className="form-actions">
          <button
            type="button"
            disabled={busy || !batchId || !received}
            onClick={() =>
              void run(
                () =>
                  api.settlementReconcile({
                    batch_id: batchId.trim(),
                    received_amount: Number(received),
                  }),
                "Batch reconciled.",
              )
            }
          >
            Reconcile
          </button>
        </div>
      </article>

      <article className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>Recent batches</h2>
          <button type="button" className="secondary" onClick={() => void loadBatches()}>
            Refresh
          </button>
        </div>
        {batches.length === 0 && <p className="muted">No settlement batches yet.</p>}
        {batches.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Batch</th>
                  <th>Status</th>
                  <th>Payer</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {batches.map((b) => (
                  <tr key={b.id}>
                    <td>{b.batch_number || b.id}</td>
                    <td>{b.status}</td>
                    <td className="muted small">{String(b.payer_id || "").slice(0, 8)}…</td>
                    <td>
                      <button type="button" className="secondary" onClick={() => setBatchId(b.id)}>
                        Use
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>

      <article className="card">
        <h2>Result</h2>
        <pre className="muted small" style={{ whiteSpace: "pre-wrap" }}>
          {message || "No operation run yet."}
        </pre>
        <p className="muted small">Developed by BAHATI GAD WANGWE · Phase 116</p>
      </article>
    </section>
  );
}
