import { Link } from "react-router-dom";
import { KenyaFlag } from "../components/KenyaFlag";

export function EntryPage() {
  return (
    <div className="portal-page">
      <div className="portal-shell">
        <div className="portal-card">
          <div className="portal-brand">
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

          <div className="portal-actions">
            <Link to="/login/facility" className="portal-tile">
              <strong>Facility / Staff</strong>
              <p className="muted small">
                Clinicians, administrators and facility teams. Requires facility workspace.
              </p>
            </Link>
            <Link to="/login/patient" className="portal-tile">
              <strong>Patient</strong>
              <p className="muted small">
                View records, book appointments, message hospitals. Sign in with Afya ID or SHA
                number.
              </p>
            </Link>
          </div>

          <p className="muted small auth-note">
            © {new Date().getFullYear()} AfyaSync. Developed by <strong>BAHATI GAD WANGWE</strong>.
          </p>
        </div>
      </div>
    </div>
  );
}
