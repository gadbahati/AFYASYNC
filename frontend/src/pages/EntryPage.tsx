import { Link } from "react-router-dom";
import { KenyaFlag } from "../components/KenyaFlag";

export function EntryPage() {
  return (
    <main className="auth-page" aria-label="AfyaSync sign in options">
      <div className="card auth-card">
        <div className="auth-brand">
          <KenyaFlag />
          <div>
            <div className="brand-kicker">Republic of Kenya</div>
            <h1>AfyaSync</h1>
          </div>
        </div>
        <div>
          <h2>Who is signing in?</h2>
          <p className="muted">Choose how you want to access AfyaSync.</p>
        </div>

        <div className="entry-choices" style={{ display: "grid", gap: "1rem", marginTop: "1.25rem" }}>
          <Link
            to="/login/facility"
            className="entry-choice"
            style={{
              display: "block",
              padding: "1rem 1.25rem",
              border: "1px solid var(--border, #d0d7de)",
              borderRadius: "8px",
              textDecoration: "none",
              color: "inherit",
            }}
          >
            <strong>Facility / Staff</strong>
            <p className="muted small" style={{ margin: "0.35rem 0 0" }}>
              Clinicians, administrators and facility teams. Requires facility workspace.
            </p>
          </Link>

          <Link
            to="/login/patient"
            className="entry-choice"
            style={{
              display: "block",
              padding: "1rem 1.25rem",
              border: "1px solid var(--border, #d0d7de)",
              borderRadius: "8px",
              textDecoration: "none",
              color: "inherit",
            }}
          >
            <strong>Patient</strong>
            <p className="muted small" style={{ margin: "0.35rem 0 0" }}>
              View your records, coverage and disclosure decisions. Sign in with Afya ID or SHA number.
            </p>
          </Link>
        </div>

        <p className="muted small auth-note" style={{ marginTop: "1.5rem" }}>
          © {new Date().getFullYear()} AfyaSync. Developed by Bahati GAD Wangwe.
        </p>
      </div>
    </main>
  );
}
