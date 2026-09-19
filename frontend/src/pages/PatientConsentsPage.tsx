import { useEffect, useState, type FormEvent } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

type Consent = {
  id: string;
  disease_label?: string;
  category_code?: string;
  consent_given: boolean;
  share_scope?: string;
  consented_at?: string;
  notes?: string | null;
};

export function PatientConsentsPage() {
  const auth = useAuth();
  const [items, setItems] = useState<Consent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Consent | null>(null);
  const [consentGiven, setConsentGiven] = useState(true);
  const [signature, setSignature] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [ok, setOk] = useState<string | null>(null);

  async function load() {
    const res = await api.portalConsents();
    setItems(res.items || []);
  }

  useEffect(() => {
    if (auth.accountType !== "patient") return;
    load().catch((e: unknown) =>
      setError(e instanceof ApiError ? e.message || e.code : "Unable to load consents"),
    );
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

  function startEdit(c: Consent) {
    setEditing(c);
    setConsentGiven(c.consent_given);
    setSignature("");
    setNotes(c.notes || "");
    setOk(null);
    setError(null);
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (!editing || signature.trim().length < 2) {
      setError("Type your full name as digital signature to confirm.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.portalUpdateConsent(editing.id, {
        consent_given: consentGiven,
        signature_data: signature.trim(),
        signature_method: "ON_SCREEN_NAME",
        notes: notes || undefined,
      });
      setOk("Disclosure decision updated.");
      setEditing(null);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Update failed");
    } finally {
      setSaving(false);
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
              <h1>Sensitive disclosure</h1>
            </div>
          </div>
          <p className="muted">
            Some conditions are sensitive. You choose whether other hospitals can see them when your
            ID is searched. Changing a decision requires your signature on this screen.
          </p>

          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
          {ok && <div className="success-box">{ok}</div>}

          {items.length === 0 ? (
            <p className="muted small">No sensitive disclosure decisions recorded yet.</p>
          ) : (
            <ul className="portal-list">
              {items.map((c) => (
                <li key={c.id} className="portal-list-item">
                  <div className="row-between">
                    <strong>{c.disease_label || c.category_code || "Sensitive condition"}</strong>
                    <span
                      className={`portal-status ${c.consent_given ? "accepted" : "declined"}`}
                    >
                      {c.consent_given ? "Share across facilities" : "This facility only"}
                    </span>
                  </div>
                  {c.consented_at && (
                    <p className="muted small">
                      Decided {new Date(c.consented_at).toLocaleString()}
                    </p>
                  )}
                  <button type="button" className="secondary" onClick={() => startEdit(c)}>
                    Change decision
                  </button>
                </li>
              ))}
            </ul>
          )}

          {editing && (
            <form className="portal-form" onSubmit={onSave}>
              <h3>Update decision</h3>
              <p className="small muted">{editing.disease_label || editing.category_code}</p>
              <label>
                Allow other hospitals to see this condition?
                <select
                  value={consentGiven ? "yes" : "no"}
                  onChange={(e) => setConsentGiven(e.target.value === "yes")}
                >
                  <option value="yes">Yes — share across facilities</option>
                  <option value="no">No — keep at treating facility only</option>
                </select>
              </label>
              <label>
                Digital signature (type your full name)
                <input
                  value={signature}
                  onChange={(e) => setSignature(e.target.value)}
                  required
                  minLength={2}
                  placeholder="Your full name"
                />
              </label>
              <label>
                Notes (optional)
                <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
              </label>
              <div className="form-actions">
                <button type="submit" disabled={saving}>
                  {saving ? "Saving…" : "Sign and save"}
                </button>
                <button type="button" className="secondary" onClick={() => setEditing(null)}>
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="portal-footer-links">
            <Link to="/portal">Back to portal</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
