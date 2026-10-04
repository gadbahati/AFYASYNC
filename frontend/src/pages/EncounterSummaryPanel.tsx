/** Phase 137 — print-ready clinical encounter summary. Developed by BAHATI GAD WANGWE */
import { useCallback, useEffect, useState } from "react";
import { ApiError, request } from "../api/client";

type Props = { encounterId: string };

export function EncounterSummaryPanel({ encounterId }: Props) {
  const [summary, setSummary] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await request(`/api/v1/encounters/${encounterId}/summary`);
      setSummary(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "SUMMARY_FAILED");
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [encounterId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  function onPrint() {
    window.print();
  }

  return (
    <section className="card clinical-summary-print" id="clinical-summary-print">
      <div className="report-card-header">
        <div>
          <h2 style={{ margin: 0 }}>Clinical summary</h2>
          <p className="muted small">Phase 137 · Handout / print view</p>
        </div>
        <div className="actions">
          <button type="button" className="secondary" disabled={loading} onClick={() => void reload()}>
            Refresh
          </button>
          <button type="button" disabled={!summary || loading} onClick={onPrint}>
            Print summary
          </button>
        </div>
      </div>

      {loading && <p>Loading summary…</p>}
      {error && <div className="error">{error}</div>}

      {summary && (
        <div className="summary-body">
          <div className="detail-grid">
            <div>
              <div className="muted small">Facility</div>
              <div>
                <strong>{summary.facility?.name || "—"}</strong>
                {summary.facility?.code ? ` (${summary.facility.code})` : ""}
              </div>
            </div>
            <div>
              <div className="muted small">Patient</div>
              <div>
                <strong>{summary.patient?.name || "—"}</strong>
                {summary.patient?.afya_id ? ` · ${summary.patient.afya_id}` : ""}
              </div>
            </div>
            <div>
              <div className="muted small">Encounter</div>
              <div>
                {summary.encounter?.encounter_id || summary.encounter?.id} · {summary.encounter?.type} ·{" "}
                <span className="status-pill">{summary.encounter?.status}</span>
              </div>
            </div>
            <div>
              <div className="muted small">Generated</div>
              <div>
                {summary.generated_at
                  ? new Date(summary.generated_at).toLocaleString("en-KE")
                  : "—"}
              </div>
            </div>
          </div>

          {summary.diagnoses?.length > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <h3>Diagnoses</h3>
              <ul className="plain-list">
                {summary.diagnoses.map((d: any, i: number) => (
                  <li key={d.id || i}>
                    {d.diagnosis_type || ""}: {d.diagnosis_name || d.name || "—"}{" "}
                    {d.diagnosis_code ? `(${d.diagnosis_code})` : ""}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {summary.consultation && (
            <div style={{ marginTop: "1rem" }}>
              <h3>Consultation</h3>
              <p>
                <strong>Assessment:</strong> {summary.consultation.assessment || "—"}
              </p>
              <p>
                <strong>Plan:</strong> {summary.consultation.treatment_plan || "—"}
              </p>
            </div>
          )}

          {summary.clinical_orders?.length > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <h3>Orders</h3>
              <ul className="plain-list">
                {summary.clinical_orders.map((o: any) => (
                  <li key={o.id}>
                    {o.order_type} {o.code || ""} — {o.description} · {o.status}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {summary.discharge && (
            <div style={{ marginTop: "1rem" }}>
              <h3>Discharge</h3>
              <p>
                <strong>{summary.discharge.disposition}</strong> · {summary.discharge.outcome}
              </p>
              {summary.discharge.follow_up_instructions && (
                <p>Follow-up: {summary.discharge.follow_up_instructions}</p>
              )}
              {summary.discharge.discharge_summary && <p>{summary.discharge.discharge_summary}</p>}
            </div>
          )}

          <p className="muted small" style={{ marginTop: "1.25rem" }}>
            AfyaSync clinical summary · Developed by BAHATI GAD WANGWE
          </p>
        </div>
      )}
    </section>
  );
}
