import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { getAccessToken } from "../auth/storage";
import type { Encounter } from "../api/types";
import { useWorkspace } from "../workspaces/WorkspaceContext";

type EncounterList = { items: Encounter[]; total: number; limit: number; offset: number };

export function EncountersPage() {
  const auth = useAuth();
  const { scope } = useWorkspace();
  const [data, setData] = useState<EncounterList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!auth.ready || !auth.facilityId || !getAccessToken()) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .listEncounters(100, 0, scope)
      .then((body: EncounterList) => {
        if (!cancelled) setData(body);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message || err.code : "Unable to load encounters");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [auth.ready, auth.facilityId, scope]);

  return (
    <div>
      <header className="page-header">
        <div>
          <Link to="/" className="muted">
            ← Dashboard
          </Link>
          <h1>Encounters</h1>
          <p className="muted">
            Clinical visits under <strong>{scope}</strong> scope, with access to the full clinical timeline.
          </p>
        </div>
        <div className="actions">
          <Link className="button secondary" to="/workspace">
            Change scope
          </Link>
        </div>
      </header>
      {loading && <p>Loading encounters…</p>}
      {error && <div className="error">{error}</div>}
      {data && (
        <section className="card">
          <div className="report-card-header">
            <div>
              <h2 style={{ margin: 0 }}>Encounters ({scope})</h2>
              <p className="muted small">
                {data.total} recorded encounter{data.total === 1 ? "" : "s"}.
              </p>
            </div>
            <Link className="button" to="/patients">
              Find patient
            </Link>
          </div>
          {data.items.length === 0 ? (
            <p className="muted">No encounters found under this operating scope.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Encounter</th>
                    <th>Patient</th>
                    <th>Type</th>
                    <th>Coverage</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((encounter) => (
                    <tr key={encounter.id}>
                      <td>
                        <strong>{encounter.encounter_id}</strong>
                      </td>
                      <td>
                        <Link to={`/patients/${encounter.patient_id}`}>View patient</Link>
                      </td>
                      <td>{encounter.encounter_type.replaceAll("_", " ")}</td>
                      <td>{encounter.coverage_mode}</td>
                      <td>{encounter.status}</td>
                      <td>{new Date(encounter.started_at).toLocaleString("en-KE")}</td>
                      <td>
                        <Link to={`/encounters/${encounter.id}`}>Open clinical record →</Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
