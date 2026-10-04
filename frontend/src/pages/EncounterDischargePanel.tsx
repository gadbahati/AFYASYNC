/** Phase 136 — discharge encounter from clinical record. Developed by BAHATI GAD WANGWE */
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";

type Props = {
  encounterId: string;
  open: boolean;
  onDischarged?: () => void;
};

export function EncounterDischargePanel({ encounterId, open, onDischarged }: Props) {
  const [record, setRecord] = useState<any | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const reload = useCallback(async () => {
    try {
      const row = await api.getEncounterDischarge(encounterId);
      setRecord(row);
    } catch (err) {
      if (err instanceof ApiError && (err.status === 404 || err.code === "DISCHARGE_NOT_FOUND")) {
        setRecord(null);
      } else if (err instanceof ApiError) {
        // Not discharged yet is normal
        setRecord(null);
      } else {
        setRecord(null);
      }
    } finally {
      setLoaded(true);
    }
  }, [encounterId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const followUp = String(fd.get("follow_up_date") || "").trim();
      const row = await api.dischargeEncounter(encounterId, {
        disposition: String(fd.get("disposition") || "HOME"),
        outcome: String(fd.get("outcome") || "STABLE"),
        follow_up_instructions: String(fd.get("follow_up_instructions") || "") || undefined,
        follow_up_date: followUp || undefined,
        discharge_summary: String(fd.get("discharge_summary") || "") || undefined,
      });
      setRecord(row);
      onDischarged?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.code || err.message : "DISCHARGE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h2>Discharge</h2>
      <p className="muted small">Phase 131 / 136 · Close the clinical encounter with disposition and follow-up</p>
      {error && <div className="error">{error}</div>}

      {record && (
        <div className="detail-grid">
          <div>
            <div className="muted small">Disposition</div>
            <div>
              <strong>{record.disposition}</strong>
            </div>
          </div>
          <div>
            <div className="muted small">Outcome</div>
            <div>{record.outcome}</div>
          </div>
          <div>
            <div className="muted small">Discharged at</div>
            <div>
              {record.discharged_at
                ? new Date(record.discharged_at).toLocaleString("en-KE")
                : "—"}
            </div>
          </div>
          {record.follow_up_date && (
            <div>
              <div className="muted small">Follow-up date</div>
              <div>{record.follow_up_date}</div>
            </div>
          )}
          {record.follow_up_instructions && (
            <div className="span-2">
              <div className="muted small">Follow-up instructions</div>
              <div>{record.follow_up_instructions}</div>
            </div>
          )}
          {record.discharge_summary && (
            <div className="span-2">
              <div className="muted small">Summary</div>
              <div>{record.discharge_summary}</div>
            </div>
          )}
        </div>
      )}

      {!record && open && loaded && (
        <form className="form-grid" onSubmit={onSubmit}>
          <label>
            Disposition
            <select name="disposition" defaultValue="HOME" required>
              <option value="HOME">HOME</option>
              <option value="TRANSFER">TRANSFER</option>
              <option value="ADMIT">ADMIT</option>
              <option value="REFERRED">REFERRED</option>
              <option value="LEFT_AMA">LEFT_AMA</option>
              <option value="ABSCONDED">ABSCONDED</option>
              <option value="DIED">DIED</option>
            </select>
          </label>
          <label>
            Outcome
            <select name="outcome" defaultValue="STABLE" required>
              <option value="STABLE">STABLE</option>
              <option value="IMPROVED">IMPROVED</option>
              <option value="WORSENED">WORSENED</option>
              <option value="DECEASED">DECEASED</option>
              <option value="UNKNOWN">UNKNOWN</option>
            </select>
          </label>
          <label>
            Follow-up date
            <input name="follow_up_date" type="date" />
          </label>
          <label className="span-2">
            Follow-up instructions
            <textarea name="follow_up_instructions" rows={2} placeholder="e.g. Return in 7 days if symptoms persist" />
          </label>
          <label className="span-2">
            Discharge summary
            <textarea name="discharge_summary" rows={3} placeholder="Clinical summary at discharge" />
          </label>
          <div className="form-actions span-2">
            <button type="submit" disabled={busy}>
              {busy ? "Discharging…" : "Discharge encounter"}
            </button>
          </div>
        </form>
      )}

      {!record && !open && loaded && (
        <p className="muted">Encounter is closed. No discharge form available.</p>
      )}

      <p className="muted small">Developed by BAHATI GAD WANGWE · Phase 136</p>
    </section>
  );
}
