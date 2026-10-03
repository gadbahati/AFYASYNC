import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";

type PreauthRow = {
  id: string;
  authorization_number: string;
  person_id: string;
  coverage_id: string;
  payer_id: string;
  service_code?: string | null;
  service_type?: string | null;
  requested_amount: number;
  approved_amount: number;
  status: string;
  decision_reason?: string | null;
  external_reference?: string | null;
};

export function FinancingPreauthorizationPage() {
  const [personId, setPersonId] = useState("");
  const [coverageId, setCoverageId] = useState("");
  const [payerId, setPayerId] = useState("");
  const [serviceCode, setServiceCode] = useState("");
  const [serviceType, setServiceType] = useState("");
  const [amount, setAmount] = useState("0");
  const [result, setResult] = useState<PreauthRow | null>(null);
  const [queue, setQueue] = useState<PreauthRow[]>([]);
  const [filterStatus, setFilterStatus] = useState("PENDING");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [queueLoading, setQueueLoading] = useState(false);

  const loadQueue = useCallback(async () => {
    setQueueLoading(true);
    try {
      const rows = await api.financingPreauthList({
        status: filterStatus || undefined,
        limit: 50,
      });
      setQueue(Array.isArray(rows) ? rows : []);
    } catch {
      setQueue([]);
    } finally {
      setQueueLoading(false);
    }
  }, [filterStatus]);

  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);

  async function requestPreauth() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const row = await api.financingPreauthCreate({
        person_id: personId.trim(),
        coverage_id: coverageId.trim(),
        payer_id: payerId.trim(),
        service_code: serviceCode.trim() || null,
        service_type: serviceType.trim() || null,
        requested_amount: Number(amount || 0),
      });
      setResult(row);
      await loadQueue();
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : e instanceof Error ? e.message : "PREAUTH_REQUEST_FAILED");
    } finally {
      setLoading(false);
    }
  }

  async function decide(id: string, status: string, requestedAmount: number) {
    setLoading(true);
    setError("");
    try {
      const row = await api.financingPreauthDecide(id, {
        status,
        approved_amount: status === "REJECTED" ? 0 : Number(requestedAmount),
        external_reference: null,
      });
      setResult(row);
      await loadQueue();
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : e instanceof Error ? e.message : "PREAUTH_DECISION_FAILED");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Phase 107 · Financing preauth work queue</p>
          <h1>Preauthorization exchange</h1>
          <p className="muted">
            Request authorizations when the benefit engine marks a service CONDITIONAL, then authorize or reject from the
            facility work queue. Claims preflight blocks submit until AUTHORIZED.
          </p>
        </div>
      </header>

      {error && <div className="error">{error}</div>}

      <article className="card">
        <h2>Request preauthorization</h2>
        <div className="form-grid">
          <label>
            Person ID
            <input value={personId} onChange={(e) => setPersonId(e.target.value)} placeholder="UUID" />
          </label>
          <label>
            Coverage ID
            <input value={coverageId} onChange={(e) => setCoverageId(e.target.value)} placeholder="UUID" />
          </label>
          <label>
            Payer ID
            <input value={payerId} onChange={(e) => setPayerId(e.target.value)} placeholder="UUID" />
          </label>
          <label>
            Service code
            <input value={serviceCode} onChange={(e) => setServiceCode(e.target.value)} placeholder="e.g. MRI-BRAIN" />
          </label>
          <label>
            Service type
            <input value={serviceType} onChange={(e) => setServiceType(e.target.value)} placeholder="e.g. IMAGING" />
          </label>
          <label>
            Requested amount (KES)
            <input type="number" min="0" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </label>
        </div>
        <div className="form-actions">
          <button
            type="button"
            className="primary"
            disabled={loading || !personId || !coverageId || !payerId}
            onClick={() => void requestPreauth()}
          >
            {loading ? "Submitting…" : "Request preauthorization"}
          </button>
        </div>
      </article>

      {result && (
        <article className="card">
          <h2>
            Current authorization · {result.status}{" "}
            <span className="muted small">{result.authorization_number}</span>
          </h2>
          <div
            className="stat-grid"
            style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(140px,1fr))", gap: 12 }}
          >
            <div className="stat-card">
              <div className="muted small">Requested</div>
              <div className="stat-value">{result.requested_amount}</div>
            </div>
            <div className="stat-card">
              <div className="muted small">Approved</div>
              <div className="stat-value">{result.approved_amount}</div>
            </div>
            <div className="stat-card">
              <div className="muted small">Service</div>
              <div className="stat-value">{result.service_code || "—"}</div>
            </div>
            <div className="stat-card">
              <div className="muted small">Reason</div>
              <div className="stat-value" style={{ fontSize: 14 }}>
                {result.decision_reason || "—"}
              </div>
            </div>
          </div>
          {(result.status === "PENDING" || result.status === "SUBMITTED") && (
            <div className="form-actions" style={{ marginTop: 12 }}>
              <button type="button" disabled={loading} onClick={() => void decide(result.id, "AUTHORIZED", result.requested_amount)}>
                Authorize full amount
              </button>
              <button type="button" className="secondary" disabled={loading} onClick={() => void decide(result.id, "CONDITIONAL", result.requested_amount)}>
                Conditional
              </button>
              <button type="button" className="secondary" disabled={loading} onClick={() => void decide(result.id, "REJECTED", 0)}>
                Reject
              </button>
            </div>
          )}
        </article>
      )}

      <article className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <h2 style={{ margin: 0 }}>Work queue</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} aria-label="Filter status">
              <option value="PENDING">PENDING</option>
              <option value="SUBMITTED">SUBMITTED</option>
              <option value="AUTHORIZED">AUTHORIZED</option>
              <option value="CONDITIONAL">CONDITIONAL</option>
              <option value="REJECTED">REJECTED</option>
              <option value="">All</option>
            </select>
            <button type="button" className="secondary" disabled={queueLoading} onClick={() => void loadQueue()}>
              {queueLoading ? "Loading…" : "Refresh"}
            </button>
          </div>
        </div>
        {queue.length === 0 && <p className="muted">No preauthorizations for this filter.</p>}
        {queue.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Number</th>
                  <th>Status</th>
                  <th>Service</th>
                  <th>Requested</th>
                  <th>Approved</th>
                  <th>Person</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((row) => (
                  <tr key={row.id}>
                    <td>{row.authorization_number}</td>
                    <td>{row.status}</td>
                    <td>{row.service_code || row.service_type || "—"}</td>
                    <td>{row.requested_amount}</td>
                    <td>{row.approved_amount}</td>
                    <td className="muted small">{row.person_id.slice(0, 8)}…</td>
                    <td>
                      <button type="button" className="linkish" onClick={() => setResult(row)}>
                        Open
                      </button>
                      {(row.status === "PENDING" || row.status === "SUBMITTED") && (
                        <>
                          {" · "}
                          <button
                            type="button"
                            className="linkish"
                            disabled={loading}
                            onClick={() => void decide(row.id, "AUTHORIZED", row.requested_amount)}
                          >
                            Authorize
                          </button>
                          {" · "}
                          <button
                            type="button"
                            className="linkish"
                            disabled={loading}
                            onClick={() => void decide(row.id, "REJECTED", 0)}
                          >
                            Reject
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="muted small" style={{ marginTop: 12 }}>
          Developed by BAHATI GAD WANGWE · AfyaSync financing preauth
        </p>
      </article>
    </section>
  );
}

export default FinancingPreauthorizationPage;
