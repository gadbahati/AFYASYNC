import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { QueueEntry } from "../api/types";

export function QueuePage() {
  const [rows, setRows] = useState<QueueEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const data = await api.listQueueEntries();
    setRows(data);
  }, []);

  useEffect(() => {
    let cancelled = false;
    reload()
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.code : "LOAD_FAILED");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reload]);

  async function setStatus(entryId: string, status: string) {
    setBusyId(entryId);
    setError(null);
    try {
      await api.updateQueueEntryStatus(entryId, status);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "UPDATE_FAILED");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h1>Queue</h1>
          <p className="muted">Patients waiting or in service</p>
        </div>
      </header>
      {loading && <p>Loading…</p>}
      {error && <div className="error">{error}</div>}
      {!loading && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Queued</th>
                <th>Patient ID</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.id}>
                  <td>{new Date(e.queued_at).toLocaleString()}</td>
                  <td>{e.patient_id}</td>
                  <td>{e.priority}</td>
                  <td>{e.status}</td>
                  <td>
                    <div className="actions">
                      {e.status === "WAITING" && (
                        <button type="button" disabled={busyId === e.id} onClick={() => void setStatus(e.id, "CALLED")}>
                          Call
                        </button>
                      )}
                      {e.status === "CALLED" && (
                        <button type="button" disabled={busyId === e.id} onClick={() => void setStatus(e.id, "IN_SERVICE")}>
                          Start
                        </button>
                      )}
                      {e.status === "IN_SERVICE" && (
                        <button type="button" disabled={busyId === e.id} onClick={() => void setStatus(e.id, "COMPLETED")}>
                          Complete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="muted">No queue entries right now.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
