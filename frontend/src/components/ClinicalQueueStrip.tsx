/** Phase 155 — open LAB / PHARMACY / IMAGING queue counters.
 *  Developed by BAHATI GAD WANGWE
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { request } from "../api/client";

type Counts = { LAB: number; PHARMACY: number; IMAGING: number };

async function countType(orderType: string): Promise<number> {
  try {
    const body = await request(`/api/v1/clinical/worklist?order_type=${encodeURIComponent(orderType)}`);
    if (typeof body?.count === "number") return body.count;
    return Array.isArray(body?.items) ? body.items.length : 0;
  } catch {
    return 0;
  }
}

export function ClinicalQueueStrip() {
  const [counts, setCounts] = useState<Counts | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([countType("LAB"), countType("PHARMACY"), countType("IMAGING")])
      .then(([lab, rx, img]) => {
        if (!cancelled) setCounts({ LAB: lab, PHARMACY: rx, IMAGING: img });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const total = counts ? counts.LAB + counts.PHARMACY + counts.IMAGING : 0;

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
          <Link
            className="stat-card"
            to="/radiology"
            style={{ textDecoration: "none", color: "inherit" }}
          >
            <div className="muted small">Imaging</div>
            <div className="stat-value">{counts.IMAGING}</div>
          </Link>
          <div className="stat-card">
            <div className="muted small">Total open</div>
            <div className="stat-value">{total}</div>
          </div>
        </div>
      )}
      <p className="muted small" style={{ marginTop: "0.5rem" }}>
        Developed by BAHATI GAD WANGWE · Phase 155
      </p>
    </section>
  );
}
