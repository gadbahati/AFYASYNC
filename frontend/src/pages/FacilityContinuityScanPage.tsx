import { FormEvent, useState } from "react";
import { api, ApiError } from "../api/client";

type Snapshot = {
  afya_id?: string | null;
  display_name: string;
  sex?: string | null;
  date_of_birth?: string | null;
  blood_type?: string | null;
  allergies: { substance?: string; severity?: string; reaction?: string }[];
  shared_diagnoses: { code?: string; description?: string; sensitive?: boolean }[];
  consent_note?: string | null;
};

export function FacilityContinuityScanPage() {
  const [token, setToken] = useState("");
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = token.trim();
    if (t.length < 16) {
      setError("Enter a valid continuity token (min 16 characters).");
      return;
    }
    setBusy(true);
    setError(null);
    setSnapshot(null);
    try {
      const res = await api.facilityContinuityScan(t);
      setSnapshot(res.snapshot);
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "SCAN_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">Patients & care</p>
          <h1>Continuity card scan</h1>
          <p className="muted">
            Verify a patient wallet token. Sensitive diagnoses appear only with CROSS_FACILITY consent.
          </p>
        </div>
      </header>

      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}

      <article className="card">
        <form className="form-grid" onSubmit={onSubmit}>
          <label className="span-2">
            Continuity token
            <input
              value={token}
              onChange={(e) => setToken(e.target.value)}
              autoComplete="off"
              spellCheck={false}
              placeholder="Paste or type token from patient QR / card"
            />
          </label>
          <div className="form-actions span-2">
            <button type="submit" disabled={busy}>
              Scan / verify
            </button>
          </div>
        </form>
      </article>

      {snapshot && (
        <article className="card">
          <h2 style={{ marginTop: 0 }}>{snapshot.display_name}</h2>
          {snapshot.afya_id && <p className="muted small">Afya ID: {snapshot.afya_id}</p>}
          <p className="small muted">
            {[snapshot.sex, snapshot.date_of_birth, snapshot.blood_type].filter(Boolean).join(" · ")}
          </p>

          <h3>Allergies</h3>
          {snapshot.allergies?.length ? (
            <ul>
              {snapshot.allergies.map((a, i) => (
                <li key={i}>
                  <strong>{a.substance || "Allergen"}</strong>
                  {a.severity ? ` (${a.severity})` : ""}
                  {a.reaction ? ` — ${a.reaction}` : ""}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted small">None recorded.</p>
          )}

          <h3>Shared diagnoses</h3>
          {snapshot.shared_diagnoses?.length ? (
            <ul>
              {snapshot.shared_diagnoses.map((d, i) => (
                <li key={i}>
                  <strong>{d.code || "—"}</strong> {d.description}
                  {d.sensitive ? " [sensitive, consented]" : ""}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted small">None shared across facilities.</p>
          )}

          {snapshot.consent_note && <p className="small muted">{snapshot.consent_note}</p>}
        </article>
      )}
    </section>
  );
}
