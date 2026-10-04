/** Phase 147 — Imaging workbench with modality + impression. Developed by BAHATI GAD WANGWE */
import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ApiError, request } from "../api/client";

type WorkItem = {
  id: string;
  order_type?: string;
  code?: string;
  description?: string;
  priority?: string;
  status?: string;
  encounter_id?: string;
  patient_id?: string;
};

const MODALITIES = ["XR", "CT", "MRI", "US", "FLUORO", "MAMMO", "NM", "OTHER"];

export function RadiologyPage() {
  const [params] = useSearchParams();
  const focusOrderId = params.get("orderId") || "";
  const focusEncounterId = params.get("encounterId") || "";
  const focusPatientId = params.get("patientId") || "";

  const [items, setItems] = useState<WorkItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [modality, setModality] = useState("XR");
  const [impression, setImpression] = useState("");
  const [activeId, setActiveId] = useState<string | null>(focusOrderId || null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body = await request("/api/v1/clinical/worklist/imaging");
      let list: WorkItem[] = body.items || [];
      if (focusOrderId) {
        list = [...list].sort((a, b) => (a.id === focusOrderId ? -1 : b.id === focusOrderId ? 1 : 0));
      } else if (focusEncounterId) {
        list = [...list].sort((a, b) =>
          a.encounter_id === focusEncounterId ? -1 : b.encounter_id === focusEncounterId ? 1 : 0,
        );
      } else if (focusPatientId) {
        list = [...list].sort((a, b) =>
          a.patient_id === focusPatientId ? -1 : b.patient_id === focusPatientId ? 1 : 0,
        );
      }
      setItems(list);
      if (!activeId && list[0]) setActiveId(list[0].id);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "IMAGING_WORKLIST_FAILED");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [focusOrderId, focusEncounterId, focusPatientId, activeId]);

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusOrderId, focusEncounterId, focusPatientId]);

  async function forwardOrder(id: string) {
    setBusyId(id);
    setMsg(null);
    try {
      await request(`/api/v1/encounters/orders/${id}/forward`, { method: "POST" });
      setMsg(`Forwarded ${id.slice(0, 8)}…`);
      await reload();
    } catch (err) {
      setMsg(err instanceof ApiError ? err.code : "FORWARD_FAILED");
    } finally {
      setBusyId(null);
    }
  }

  async function completeOrder(id: string) {
    if (!impression.trim()) {
      setMsg("Enter an impression before completing the study");
      return;
    }
    setBusyId(id);
    setMsg(null);
    try {
      await request(`/api/v1/encounters/orders/${id}/fulfill`, {
        method: "POST",
        body: JSON.stringify({
          status: "COMPLETED",
          modality,
          impression: impression.trim(),
          result_notes: "Imaging report filed from radiology workbench",
        }),
      });
      setMsg(`Completed ${id.slice(0, 8)}… · ${modality}`);
      setImpression("");
      await reload();
    } catch (err) {
      setMsg(err instanceof ApiError ? err.code : "FULFILL_FAILED");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <Link to="/clinical-worklist" className="muted">
            ← Clinical worklist
          </Link>
          <h1>Radiology / imaging</h1>
          <p className="muted">Report modality + impression, then complete study</p>
          {(focusOrderId || focusEncounterId || focusPatientId) && (
            <p className="muted small">
              Focus:{" "}
              {focusPatientId && (
                <Link to={`/patients/${focusPatientId}`}>patient {focusPatientId.slice(0, 8)}…</Link>
              )}
              {focusPatientId && (focusOrderId || focusEncounterId) ? " · " : ""}
              {focusEncounterId && (
                <Link to={`/encounters/${focusEncounterId}`}>encounter {focusEncounterId.slice(0, 8)}…</Link>
              )}
              {focusEncounterId && focusOrderId ? " · " : ""}
              {focusOrderId ? `order ${focusOrderId.slice(0, 8)}…` : ""}
            </p>
          )}
        </div>
        <button type="button" className="secondary" onClick={() => void reload()} disabled={loading}>
          Refresh
        </button>
      </header>

      <section className="card" style={{ marginBottom: "1rem" }}>
        <h2>Report entry</h2>
        <div className="form-row" style={{ display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
          <label>
            Modality{" "}
            <select value={modality} onChange={(e) => setModality(e.target.value)} aria-label="Modality">
              {MODALITIES.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label style={{ display: "block", marginTop: "0.5rem" }}>
          Impression
          <textarea
            value={impression}
            onChange={(e) => setImpression(e.target.value)}
            rows={4}
            style={{ width: "100%", marginTop: "0.25rem" }}
            placeholder="Findings and impression for the selected study…"
          />
        </label>
        <p className="muted small">Select a queue item below, enter impression, then Complete study.</p>
      </section>

      {loading && <p>Loading imaging queue…</p>}
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {msg && (
        <p className="muted" role="status">
          {msg}
        </p>
      )}

      <section className="card">
        <h2>Queue ({items.length})</h2>
        <ul className="plain-list">
          {items.map((o) => {
            const focused =
              o.id === activeId ||
              o.id === focusOrderId ||
              o.encounter_id === focusEncounterId ||
              o.patient_id === focusPatientId;
            return (
              <li
                key={o.id}
                style={{
                  marginBottom: "0.75rem",
                  padding: focused ? "0.5rem" : undefined,
                  border: focused ? "1px solid var(--border, #ccc)" : undefined,
                  borderRadius: focused ? "6px" : undefined,
                  cursor: "pointer",
                }}
                onClick={() => setActiveId(o.id)}
              >
                <div>
                  <strong>{o.code || "IMAGING"}</strong> — {o.description} · {o.priority || "ROUTINE"} ·{" "}
                  <span className="status-pill">{o.status}</span>
                  {o.id === activeId && <span className="muted small"> · selected</span>}
                </div>
                <div className="actions" style={{ marginTop: "0.35rem", flexWrap: "wrap", gap: "0.35rem" }}>
                  {o.patient_id && (
                    <Link className="button secondary" to={`/patients/${o.patient_id}`} onClick={(e) => e.stopPropagation()}>
                      Patient
                    </Link>
                  )}
                  {o.encounter_id && (
                    <Link
                      className="button secondary"
                      to={`/encounters/${o.encounter_id}`}
                      onClick={(e) => e.stopPropagation()}
                    >
                      Encounter
                    </Link>
                  )}
                  {(o.status === "ORDERED" || o.status === "IN_PROGRESS") && (
                    <>
                      <button
                        type="button"
                        className="secondary"
                        disabled={busyId === o.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          void forwardOrder(o.id);
                        }}
                      >
                        Forward
                      </button>
                      <button
                        type="button"
                        disabled={busyId === o.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveId(o.id);
                          void completeOrder(o.id);
                        }}
                      >
                        Complete study
                      </button>
                    </>
                  )}
                </div>
              </li>
            );
          })}
          {items.length === 0 && !loading && <li className="muted">No open imaging orders.</li>}
        </ul>
        <p className="muted small">Developed by BAHATI GAD WANGWE · Phase 147</p>
      </section>
    </div>
  );
}
