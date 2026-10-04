/** Phase 139 — clinical department worklist. Developed by BAHATI GAD WANGWE */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, request } from "../api/client";

export function ClinicalWorklistPage() {
  const [orderType, setOrderType] = useState("IMAGING");
  const [data, setData] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

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

  return (
    <div>
      <header className="page-header">
        <div>
          <Link to="/" className="muted">
            ← Dashboard
          </Link>
          <h1>Clinical worklist</h1>
          <p className="muted">Department queue for LAB / PHARMACY / IMAGING orders</p>
        </div>
        <div className="actions">
          <select value={orderType} onChange={(e) => setOrderType(e.target.value)}>
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
      {error && <div className="error">{error}</div>}
      {data && (
        <section className="card">
          <h2>
            Queue ({data.count ?? 0}) · {data.order_type || "ALL"}
          </h2>
          <ul className="plain-list">
            {(data.items || []).map((o: any) => (
              <li key={o.id}>
                <strong>{o.order_type}</strong> {o.code || ""} — {o.description} · {o.priority} ·{" "}
                <span className="status-pill">{o.status}</span>
                {o.encounter_id && (
                  <>
                    {" "}
                    <Link to={`/encounters/${o.encounter_id}`}>Open encounter</Link>
                  </>
                )}
              </li>
            ))}
            {(data.items || []).length === 0 && <li className="muted">No open orders in this queue.</li>}
          </ul>
          <p className="muted small">Developed by BAHATI GAD WANGWE · Phase 139</p>
        </section>
      )}
    </div>
  );
}
