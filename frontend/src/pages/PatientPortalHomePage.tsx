import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

type Profile = {
  first_name: string;
  last_name: string;
  afya_id?: string | null;
  phone?: string | null;
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
      <div className="auth-page">
        <div className="card auth-card">
          <p className="muted">Loading…</p>
        </div>
      </div>
    );
  }

  if (!auth.username || auth.accountType !== "patient") {
    return <Navigate to="/login/patient" replace />;
  }

  return (
    <main className="auth-page" style={{ alignItems: "flex-start", paddingTop: "2rem" }}>
      <div className="card auth-card" style={{ maxWidth: "32rem", width: "100%" }}>
        <div className="auth-brand">
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
            {profile.afya_id && <p className="muted">Afya ID: {profile.afya_id}</p>}
          </div>
        ) : (
          <p className="muted">{error || "Loading your profile…"}</p>
        )}

        <div style={{ display: "grid", gap: "0.75rem", marginTop: "1.25rem" }}>
          <Link to="/portal/encounters" className="entry-choice" style={linkStyle}>
            <strong>My visits</strong>
            <p className="muted small" style={{ margin: "0.25rem 0 0" }}>
              Encounters and clinical summaries
            </p>
          </Link>
          <Link to="/portal/consents" className="entry-choice" style={linkStyle}>
            <strong>Sensitive disclosure decisions</strong>
            <p className="muted small" style={{ margin: "0.25rem 0 0" }}>
              {consentsCount != null ? `${consentsCount} recorded` : "Manage what can be shared across facilities"}
            </p>
          </Link>
          <Link to="/portal/coverage" className="entry-choice" style={linkStyle}>
            <strong>My coverage</strong>
            <p className="muted small" style={{ margin: "0.25rem 0 0" }}>
              SHA and other membership details
            </p>
          </Link>
        </div>

        <button type="button" className="linkish" style={{ marginTop: "1.5rem" }} onClick={() => void auth.logout()}>
          Sign out
        </button>

        <p className="muted small auth-note" style={{ marginTop: "1rem" }}>
          © {new Date().getFullYear()} AfyaSync. Developed by Bahati GAD Wangwe.
        </p>
      </div>
    </main>
  );
}

const linkStyle: React.CSSProperties = {
  display: "block",
  padding: "0.85rem 1rem",
  border: "1px solid var(--border, #d0d7de)",
  borderRadius: "8px",
  textDecoration: "none",
  color: "inherit",
};
