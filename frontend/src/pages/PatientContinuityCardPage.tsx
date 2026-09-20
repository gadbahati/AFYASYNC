import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

type CardMeta = {
  id: string;
  token_prefix: string;
  is_active: boolean;
  expires_at: string;
  last_verified_at?: string | null;
  verify_count: number;
  revoked_at?: string | null;
};

export function PatientContinuityCardPage() {
  const auth = useAuth();
  const [cards, setCards] = useState<CardMeta[]>([]);
  const [issuedToken, setIssuedToken] = useState<string | null>(null);
  const [verifyPath, setVerifyPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const data = await api.portalContinuityCards();
      setCards(Array.isArray(data?.items) ? data.items : []);
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "LOAD_FAILED");
    }
  }

  useEffect(() => {
    if (auth.accountType === "patient") void load();
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

  if (!auth.username || auth.accountType !== "patient") {
    return <Navigate to="/login/patient" replace />;
  }

  async function issue() {
    setBusy(true);
    setError(null);
    setMessage(null);
    setIssuedToken(null);
    try {
      const res = await api.portalIssueContinuityCard();
      setIssuedToken(res.token);
      setVerifyPath(res.verify_path);
      setMessage("New continuity card issued. Save the token now — it is shown only once.");
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "ISSUE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string) {
    setBusy(true);
    setError(null);
    try {
      await api.portalRevokeContinuityCard(id);
      setMessage("Card revoked.");
      setIssuedToken(null);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "REVOKE_FAILED");
    } finally {
      setBusy(false);
    }
  }

  const qrUrl =
    issuedToken && typeof window !== "undefined"
      ? `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(
          `${window.location.origin}/continuity/${issuedToken}`,
        )}`
      : null;

  return (
    <div className="portal-page">
      <div className="portal-shell wide">
        <div className="portal-card">
          <div className="portal-brand">
            <KenyaFlag />
            <div>
              <div className="brand-kicker">Patient portal</div>
              <h1>Continuity card</h1>
            </div>
          </div>

          <p className="muted small">
            Your consent-aware health wallet. Hospitals can verify the token and only see diagnoses you
            agreed to share across facilities. Sensitive conditions stay private unless you signed
            CROSS_FACILITY disclosure.
          </p>

          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
          {message && <div className="success-box">{message}</div>}

          <button type="button" disabled={busy} onClick={() => void issue()}>
            Issue new card
          </button>

          {issuedToken && (
            <div className="card" style={{ marginTop: 12 }}>
              <h3 style={{ marginTop: 0 }}>Save this token</h3>
              <p className="mono" style={{ wordBreak: "break-all", fontSize: 14 }}>
                {issuedToken}
              </p>
              {verifyPath && (
                <p className="small muted">
                  Link: <Link to={verifyPath}>{verifyPath}</Link>
                </p>
              )}
              {qrUrl && (
                <div style={{ marginTop: 12, textAlign: "center" }}>
                  <img src={qrUrl} alt="Continuity card QR code" width={220} height={220} />
                  <p className="small muted">Scan at a facility reception desk</p>
                </div>
              )}
            </div>
          )}

          <h3>Your cards</h3>
          {cards.length === 0 ? (
            <p className="muted small">No cards yet. Issue one to carry allergies and shared history.</p>
          ) : (
            <ul className="portal-list">
              {cards.map((c) => (
                <li key={c.id} className="portal-list-item">
                  <strong className="mono">{c.token_prefix}…</strong>{" "}
                  <span className={c.is_active ? "portal-status accepted" : "portal-status declined"}>
                    {c.is_active ? "ACTIVE" : "REVOKED"}
                  </span>
                  <p className="portal-meta">
                    Expires {new Date(c.expires_at).toLocaleDateString()} · Verified {c.verify_count}{" "}
                    times
                  </p>
                  {c.is_active && (
                    <button
                      type="button"
                      className="secondary"
                      disabled={busy}
                      onClick={() => void revoke(c.id)}
                    >
                      Revoke
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}

          <div className="portal-footer-links">
            <Link to="/portal">← Portal home</Link>
            <Link to="/portal/consents">Manage consents</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
