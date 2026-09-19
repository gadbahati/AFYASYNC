import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

type EncounterRow = {
  id: string;
  facility_id?: string;
  encounter_type?: string;
  status?: string;
  reason?: string | null;
  started_at?: string;
};

type Summary = {
  encounter: EncounterRow;
  vitals: any[];
  consultation: any | null;
  diagnoses: any[];
  lab_orders: any[];
  prescriptions: any[];
};

export function PatientVisitsPage() {
  const auth = useAuth();
  const [items, setItems] = useState<EncounterRow[]>([]);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (auth.accountType !== "patient") return;
    setLoading(true);
    api
      .portalEncounters()
      .then((res: any) => {
        setItems(res.items || res || []);
        setTotal(res.total ?? (res.items || []).length);
      })
      .catch((e: unknown) =>
        setError(e instanceof ApiError ? e.message || e.code : "Unable to load visits"),
      )
      .finally(() => setLoading(false));
  }, [auth.accountType]);

  if (!auth.ready) {
    return (
      <div className="portal-page">
        <div className="portal-shell">
          <div className="portal-card">
            <p className="muted">Loading…</p>
          </div>
        </div>
      </div>
    );
  }
  if (auth.accountType !== "patient") return <Navigate to="/login/patient" replace />;

  async function openVisit(id: string) {
    setError(null);
    try {
      const summary = await api.portalEncounterSummary(id);
      setSelected(summary);
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "Unable to open visit");
    }
  }

  return (
    <div className="portal-page">
      <div className="portal-shell wide">
        <div className="portal-card">
          <div className="portal-brand">
            <KenyaFlag />
            <div>
              <div className="brand-kicker">Patient portal</div>
              <h1>My visits</h1>
            </div>
          </div>
          <p className="muted">Your encounters across facilities. Tap one for a summary.</p>

          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}

          {loading ? (
            <p className="muted">Loading visits…</p>
          ) : items.length === 0 ? (
            <p className="muted small">No visits recorded yet.</p>
          ) : (
            <>
              <p className="portal-meta">{total} visit{total === 1 ? "" : "s"}</p>
              <ul className="portal-list">
                {items.map((e) => (
                  <li key={e.id} className="portal-list-item">
                    <button
                      type="button"
                      className="portal-thread-btn"
                      onClick={() => void openVisit(e.id)}
                    >
                      <strong>
                        {e.encounter_type || "Visit"} · {e.status || "—"}
                      </strong>
                      <div className="muted small">
                        {e.started_at
                          ? new Date(e.started_at).toLocaleString()
                          : "Date not set"}
                        {e.reason ? ` — ${e.reason}` : ""}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}

          {selected && (
            <div className="notice" style={{ marginTop: 8 }}>
              <div className="row-between">
                <h3 style={{ margin: 0, textTransform: "none", letterSpacing: 0, fontSize: 14 }}>
                  Visit summary
                </h3>
                <button type="button" className="secondary" onClick={() => setSelected(null)}>
                  Close
                </button>
              </div>
              <p className="small muted">
                {selected.encounter.started_at
                  ? new Date(selected.encounter.started_at).toLocaleString()
                  : ""}{" "}
                · {selected.encounter.status}
              </p>
              {selected.diagnoses?.length > 0 && (
                <>
                  <p className="section-title">Diagnoses</p>
                  <ul className="plain-list">
                    {selected.diagnoses.map((d: any, i: number) => (
                      <li key={d.id || i}>
                        {d.description || d.icd_code || d.code || "Diagnosis"}
                        {d.is_sensitive ? " (sensitive)" : ""}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {selected.consultation && (
                <>
                  <p className="section-title">Consultation</p>
                  <p className="small">
                    {selected.consultation.assessment ||
                      selected.consultation.notes ||
                      selected.consultation.plan ||
                      "Recorded"}
                  </p>
                </>
              )}
              {selected.vitals?.length > 0 && (
                <p className="small muted">{selected.vitals.length} vitals reading(s)</p>
              )}
              {selected.lab_orders?.length > 0 && (
                <p className="small muted">{selected.lab_orders.length} lab order(s)</p>
              )}
              {selected.prescriptions?.length > 0 && (
                <p className="small muted">{selected.prescriptions.length} prescription(s)</p>
              )}
            </div>
          )}

          <div className="portal-footer-links">
            <Link to="/portal">Back to portal</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
