/** Phase 142 — clinical department worklist with forward/fulfill. Developed by BAHATI GAD WANGWE */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, request } from "../api/client";

type WorkItem = {
  id: string;
  order_type?: string;
  code?: string;
  description?: string;
  priority?: string;
  status?: string;
  encounter_id?: string;
};

export function ClinicalWorklistPage() {
  const [orderType, setOrderType] = useState("IMAGING");
  const [data, setData] = useState<{ count?: number; order_type?: string; items?: WorkItem[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const q = orderType ? `?order_type=${encodeURIComponent(orderType)}` : "";
      const body = await request(`/api/v1/clinical/worklist${q}`);
      setData(body);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "WORKLIST_FAILED");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [orderType]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function forwardOrder(orderId: string) {
    setBusyId(orderId);
    setActionMsg(null);
    try {
      await request(`/api/v1/encounters/orders/${orderId}/forward`, { method: "POST" });
      setActionMsg(`Forwarded order ${orderId.slice(0, 8)}… to department`);
      await reload();
    } catch (err) {
      setActionMsg(err instanceof ApiError ? err.code : "FORWARD_FAILED");
    } finally {
      setBusyId(null);
    }
  }

  async function fulfillOrder(orderId: string) {
    setBusyId(orderId);
    setActionMsg(null);
    try {
      await request(`/api/v1/encounters/orders/${orderId}/fulfill`, {
        method: "POST",
        body: JSON.stringify({ status: "COMPLETED", result_notes: "Completed from clinical worklist" }),
      });
      setActionMsg(`Fulfilled order ${orderId.slice(0, 8)}…`);
      await reload();
    } catch (err) {
      setActionMsg(err instanceof ApiError ? err.code : "FULFILL_FAILED");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <Link to="/" className="muted">
            ← Dashboard
          </Link>
          <h1>Clinical worklist</h1>
          <p className="muted">Department queue for LAB / PHARMACY / IMAGING — forward to dept or fulfill</p>
        </div>
        <div className="actions">
          <select value={orderType} onChange={(e) => setOrderType(e.target.value)} aria-label="Order type">
            <option value="IMAGING">IMAGING</option>
            <option value="LAB">LAB</option>
            <option value="PHARMACY">PHARMACY</option>
            <option value="">All types</option>
          </select>
          <button type="button" className="secondary" onClick={() => void reload()} disabled={loading}>
            Refresh
          </button>
        </div>
      </header>

      {loading && <p>Loading worklist…</p>}
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {actionMsg && (
        <p className="muted" role="status">
          {actionMsg}
        </p>
      )}

      {data && (
        <section className="card">
          <h2>
            Queue ({data.count ?? 0}) · {data.order_type || orderType || "ALL"}
          </h2>
          <ul className="plain-list">
            {(data.items || []).map((o) => (
              <li key={o.id} style={{ marginBottom: "0.75rem" }}>
                <div>
                  <strong>{o.order_type}</strong> {o.code || ""} — {o.description} · {o.priority || "ROUTINE"} ·{" "}
                  <span className="status-pill">{o.status}</span>
                </div>
                <div className="actions" style={{ marginTop: "0.35rem" }}>
                  {o.encounter_id && (
                    <Link className="button secondary" to={`/encounters/${o.encounter_id}`}>
                      Encounter
                    </Link>
                  )}
                  {(o.status === "ORDERED" || o.status === "IN_PROGRESS") && (
                    <>
                      <button
                        type="button"
                        className="secondary"
                        disabled={busyId === o.id}
                        onClick={() => void forwardOrder(o.id)}
                      >
                        Forward to dept
                      </button>
                      <button
                        type="button"
                        disabled={busyId === o.id}
                        onClick={() => void fulfillOrder(o.id)}
                      >
                        Mark complete
                      </button>
                    </>
                  )}
                </div>
              </li>
            ))}
            {(data.items || []).length === 0 && <li className="muted">No open orders in this queue.</li>}
          </ul>
          <p className="muted small">Developed by BAHATI GAD WANGWE · Phase 142</p>
        </section>
      )}
    </div>
  );
}
