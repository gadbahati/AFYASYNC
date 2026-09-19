import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

type Profile = {
  first_name: string;
  last_name: string;
  afya_id?: string | null;
};

export function PatientPortalHomePage() {
  const auth = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [consentsCount, setConsentsCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.username || auth.accountType !== "patient") return;
    let cancelled = false;
    (async () => {
      try {
        const me = await api.portalMe();
        if (!cancelled) setProfile(me);
        const consents = await api.portalConsents();
        if (!cancelled) setConsentsCount(consents.total ?? consents.items?.length ?? 0);
      } catch {
        if (!cancelled) setError("Unable to load your portal data.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [auth.username, auth.accountType]);

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

  return (
    <div className="portal-page">
      <div className="portal-shell">
        <div className="portal-card">
          <div className="portal-brand">
            <KenyaFlag />
            <div>
              <div className="brand-kicker">Patient portal</div>
              <h1>AfyaSync</h1>
            </div>
          </div>

          {profile ? (
            <div>
              <h2>
                {profile.first_name} {profile.last_name}
              </h2>
              {profile.afya_id && <p className="portal-meta">Afya ID: {profile.afya_id}</p>}
            </div>
          ) : (
            <p className="muted">{error || "Loading your profile…"}</p>
          )}

          <div className="portal-actions">
            <Link to="/portal/book" className="portal-tile">
              <strong>Book appointment</strong>
              <p className="muted small">Choose any hospital — they accept, propose a time, or decline</p>
            </Link>
            <Link to="/portal/messages" className="portal-tile">
              <strong>Messages</strong>
              <p className="muted small">Chat with a facility about your care</p>
            </Link>
            <Link to="/portal/encounters" className="portal-tile">
              <strong>My visits</strong>
              <p className="muted small">Encounters and clinical summaries</p>
            </Link>
            <Link to="/portal/consents" className="portal-tile">
              <strong>Sensitive disclosure decisions</strong>
              <p className="muted small">
                {consentsCount != null
                  ? `${consentsCount} recorded`
                  : "Manage what can be shared across facilities"}
              </p>
            </Link>
            <Link to="/portal/coverage" className="portal-tile">
              <strong>My coverage</strong>
              <p className="muted small">SHA and other membership details</p>
            </Link>
          </div>

          <button type="button" className="portal-signout" onClick={() => void auth.logout()}>
            Sign out
          </button>

          <p className="muted small auth-note">
            © {new Date().getFullYear()} AfyaSync. Developed by Bahati GAD Wangwe.
          </p>
        </div>
      </div>
    </div>
  );
}
