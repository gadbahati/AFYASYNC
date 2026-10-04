/** Phase 143 — clinical worklist with dept deep-links + forward/fulfill.
 *  Developed by BAHATI GAD WANGWE
 */
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

/** Map clinical order type → facility department workspace path. */
function departmentPath(orderType?: string): { path: string; label: string } | null {
  const t = (orderType || "").toUpperCase();
  if (t === "LAB" || t === "LABORATORY") return { path: "/laboratory", label: "Lab workbench" };
  if (t === "PHARMACY" || t === "RX") return { path: "/pharmacy", label: "Pharmacy" };
  if (t === "IMAGING" || t === "RADIOLOGY") return { path: "/laboratory", label: "Imaging / diagnostics" };
  return null;
}

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
          <p className="muted">
            LAB → lab workbench · PHARMACY → pharmacy · IMAGING → diagnostics · forward or complete here
          </p>
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
            {(data.items || []).map((o) => {
              const dept = departmentPath(o.order_type);
              return (
                <li key={o.id} style={{ marginBottom: "0.75rem" }}>
                  <div>
                    <strong>{o.order_type}</strong> {o.code || ""} — {o.description} · {o.priority || "ROUTINE"} ·{" "}
                    <span className="status-pill">{o.status}</span>
                  </div>
                  <div className="actions" style={{ marginTop: "0.35rem", flexWrap: "wrap", gap: "0.35rem" }}>
                    {o.encounter_id && (
                      <Link className="button secondary" to={`/encounters/${o.encounter_id}`}>
                        Encounter
                      </Link>
                    )}
                    {dept && (
                      <Link className="button secondary" to={dept.path}>
                        {dept.label}
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
              );
            })}
            {(data.items || []).length === 0 && <li className="muted">No open orders in this queue.</li>}
          </ul>
          <p className="muted small">Developed by BAHATI GAD WANGWE · Phase 143</p>
        </section>
      )}
    </div>
  );
}
