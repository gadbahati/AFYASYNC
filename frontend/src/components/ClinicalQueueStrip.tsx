/** Phase 156 — open queue counters via single /worklist/counts call.
 *  Developed by BAHATI GAD WANGWE
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { request } from "../api/client";

type Counts = { LAB: number; PHARMACY: number; IMAGING: number; total: number };

export function ClinicalQueueStrip() {
  const [counts, setCounts] = useState<Counts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    request("/api/v1/clinical/worklist/counts")
      .then((body) => {
        if (cancelled) return;
        setCounts({
          LAB: Number(body.LAB || 0),
          PHARMACY: Number(body.PHARMACY || 0),
          IMAGING: Number(body.IMAGING || 0),
          total: Number(body.total ?? (body.LAB || 0) + (body.PHARMACY || 0) + (body.IMAGING || 0)),
        });
      })
      .catch(() => {
        if (!cancelled) {
          setError("QUEUE_COUNTS_UNAVAILABLE");
          setCounts({ LAB: 0, PHARMACY: 0, IMAGING: 0, total: 0 });
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="card" style={{ marginBottom: "1rem" }}>
      <div className="report-card-header" style={{ marginBottom: "0.75rem" }}>
        <div>
          <h3 style={{ margin: 0 }}>Clinical department queues</h3>
          <p className="muted small">Open LAB, pharmacy, and imaging orders for this facility</p>
        </div>
        <Link className="button secondary" to="/clinical-worklist">
          Open worklist
        </Link>
      </div>
      {loading && <p className="muted">Loading queues…</p>}
      {error && (
        <p className="muted small" role="status">
          {error}
        </p>
      )}
      {!loading && counts && (
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
        Developed by BAHATI GAD WANGWE · Phase 156
      </p>
    </section>
  );
}
