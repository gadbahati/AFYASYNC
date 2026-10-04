/** Phase 157 — queue counters with 60s auto-refresh.
 *  Developed by BAHATI GAD WANGWE
 */
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { request } from "../api/client";

type Counts = { LAB: number; PHARMACY: number; IMAGING: number; total: number };

const REFRESH_MS = 60_000;

export function ClinicalQueueStrip() {
  const [counts, setCounts] = useState<Counts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<Date | null>(null);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const body = await request("/api/v1/clinical/worklist/counts");
      setCounts({
        LAB: Number(body.LAB || 0),
        PHARMACY: Number(body.PHARMACY || 0),
        IMAGING: Number(body.IMAGING || 0),
        total: Number(body.total ?? (body.LAB || 0) + (body.PHARMACY || 0) + (body.IMAGING || 0)),
      });
      setUpdatedAt(new Date());
    } catch {
      setError("QUEUE_COUNTS_UNAVAILABLE");
      if (!silent) setCounts({ LAB: 0, PHARMACY: 0, IMAGING: 0, total: 0 });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(false);
    const id = window.setInterval(() => void load(true), REFRESH_MS);
    return () => window.clearInterval(id);
  }, [load]);

  return (
    <section className="card" style={{ marginBottom: "1rem" }}>
      <div className="report-card-header" style={{ marginBottom: "0.75rem" }}>
        <div>
          <h3 style={{ margin: 0 }}>Clinical department queues</h3>
          <p className="muted small">
            Open LAB, pharmacy, and imaging · auto-refresh every 60s
            {updatedAt ? ` · updated ${updatedAt.toLocaleTimeString("en-KE")}` : ""}
          </p>
        </div>
        <div className="actions">
          <button type="button" className="secondary" disabled={loading} onClick={() => void load(false)}>
            Refresh
          </button>
          <Link className="button secondary" to="/clinical-worklist">
            Open worklist
          </Link>
        </div>
      </div>
      {loading && !counts && <p className="muted">Loading queues…</p>}
      {error && (
        <p className="muted small" role="status">
          {error}
        </p>
      )}
      {counts && (
        <div className="stat-grid">
          <Link className="stat-card" to="/clinical-worklist?type=LAB" style={{ textDecoration: "none", color: "inherit" }}>
            <div className="muted small">Lab</div>
            <div className="stat-value">{counts.LAB}</div>
          </Link>
          <Link
            className="stat-card"
            to="/clinical-worklist?type=PHARMACY"
            style={{ textDecoration: "none", color: "inherit" }}
          >
            <div className="muted small">Pharmacy</div>
            <div className="stat-value">{counts.PHARMACY}</div>
          </Link>
          <Link className="stat-card" to="/radiology" style={{ textDecoration: "none", color: "inherit" }}>
            <div className="muted small">Imaging</div>
            <div className="stat-value">{counts.IMAGING}</div>
          </Link>
          <div className="stat-card">
            <div className="muted small">Total open</div>
            <div className="stat-value">{counts.total}</div>
          </div>
        </div>
      )}
      <p className="muted small" style={{ marginTop: "0.5rem" }}>
        Developed by BAHATI GAD WANGWE · Phase 157
      </p>
    </section>
  );
}
