import type { ReactNode } from "react";

type KesAtRisk = {
  kes_at_risk: number;
  kes_rejected: number;
  kes_in_flight: number;
  kes_draft_or_ready: number;
  count_rejected: number;
  count_in_flight: number;
  window_days: number;
};

/** Phase 116 — financing exposure banner. Developed by BAHATI GAD WANGWE */
export function ClaimsKesRiskPanel({
  kesRisk,
  money,
}: {
  kesRisk: KesAtRisk | null;
  money: (n: number | string) => string;
}): ReactNode {
  if (!kesRisk) return null;
  return (
    <article className="card">
      <h2>Financing exposure ({kesRisk.window_days}-day)</h2>
      <div className="stats-row">
        <div className="stat-card">
          <span className="muted small">Total at risk</span>
          <strong>{money(kesRisk.kes_at_risk)}</strong>
        </div>
        <div className="stat-card">
          <span className="muted small">Rejected</span>
          <strong>
            {money(kesRisk.kes_rejected)} ({kesRisk.count_rejected})
          </strong>
        </div>
        <div className="stat-card">
          <span className="muted small">In flight</span>
          <strong>
            {money(kesRisk.kes_in_flight)} ({kesRisk.count_in_flight})
          </strong>
        </div>
        <div className="stat-card">
          <span className="muted small">Draft / ready</span>
          <strong>{money(kesRisk.kes_draft_or_ready)}</strong>
        </div>
      </div>
    </article>
  );
}
