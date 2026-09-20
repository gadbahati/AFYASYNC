import { type FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { KenyaFlag } from "../components/KenyaFlag";

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

export function ContinuityVerifyPage() {
  const { token: pathToken } = useParams<{ token?: string }>();
  const [token, setToken] = useState(pathToken || "");
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [meta, setMeta] = useState<{ expires_at?: string; verify_count?: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function verify(raw: string) {
    const t = raw.trim();
    if (t.length < 16) {
      setError("Token is too short.");
      return;
    }
    setBusy(true);
    setError(null);
    setSnapshot(null);
    try {
      const res = await api.continuityVerify(t);
      setSnapshot(res.snapshot);
      setMeta({ expires_at: res.expires_at, verify_count: res.verify_count });
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "VERIFY_FAILED");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (pathToken && pathToken.length >= 16) void verify(pathToken);
  }, [pathToken]);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void verify(token);
  }

  return (
    <div className="portal-page">
      <div className="portal-shell wide">
        <div className="portal-card">
          <div className="portal-brand">
            <KenyaFlag />
            <div>
              <div className="brand-kicker">AfyaSync continuity</div>
              <h1>Verify health card</h1>
            </div>
          </div>

          <p className="muted small">
            Only information the patient authorised for cross-facility sharing is shown. Sensitive
            conditions without a signed disclosure do not appear.
          </p>

          <form className="portal-form" onSubmit={onSubmit}>
            <label>
              Continuity token
              <input
                value={token}
                onChange={(e) => setToken(e.target.value)}
                autoComplete="off"
                spellCheck={false}
                placeholder="Paste token from patient card"
              />
            </label>
            <button type="submit" disabled={busy}>
              Verify
            </button>
          </form>

          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}

          {snapshot && (
            <div className="card" style={{ marginTop: 8 }}>
              <h2 style={{ marginTop: 0 }}>{snapshot.display_name}</h2>
              {snapshot.afya_id && <p className="portal-meta">Afya ID: {snapshot.afya_id}</p>}
              <p className="small muted">
                {[snapshot.sex, snapshot.date_of_birth, snapshot.blood_type]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              {meta?.expires_at && (
                <p className="small muted">
                  Card expires {new Date(meta.expires_at).toLocaleDateString()} · scans {meta.verify_count}
                </p>
              )}

              <h3>Allergies</h3>
              {snapshot.allergies?.length ? (
                <ul className="portal-list">
                  {snapshot.allergies.map((a, i) => (
                    <li key={i} className="portal-list-item">
                      <strong>{a.substance || "Allergen"}</strong>
                      {a.severity ? ` · ${a.severity}` : ""}
                      {a.reaction ? <span className="muted small"> — {a.reaction}</span> : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted small">No active allergies on record.</p>
              )}

              <h3>Shared diagnoses</h3>
              {snapshot.shared_diagnoses?.length ? (
                <ul className="portal-list">
                  {snapshot.shared_diagnoses.map((d, i) => (
                    <li key={i} className="portal-list-item">
                      <strong>{d.code || "—"}</strong> {d.description}
                      {d.sensitive ? (
                        <span className="portal-status accepted"> shared sensitive</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted small">No cross-facility shared diagnoses.</p>
              )}

              {snapshot.consent_note && <p className="small muted">{snapshot.consent_note}</p>}
            </div>
          )}

          <div className="portal-footer-links">
            <Link to="/login">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
