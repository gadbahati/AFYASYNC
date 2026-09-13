import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "./KenyaFlag";

export function Layout() {
  const auth = useAuth();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand brand-row">
          <KenyaFlag />
          <div>
            <strong>AfyaSync</strong>
            <span className="muted">Staff console</span>
          </div>
        </div>
        <nav>
          <div className="nav-section">Overview</div>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/command-centre">Command centre</NavLink>
          <NavLink to="/coverage-simulator">Coverage simulator</NavLink>

          <div className="nav-section">Patients</div>
          <NavLink to="/patients">Patient register</NavLink>
          <NavLink to="/patients/new">Register patient</NavLink>
          <NavLink to="/patients/sha-lookup">SHA lookup</NavLink>

          <div className="nav-section">Clinical</div>
          <NavLink to="/appointments">Appointments</NavLink>
          <NavLink to="/queue">Queue</NavLink>
          <NavLink to="/benefits">Benefit packages</NavLink>

          <div className="nav-section">Laboratory & pharmacy</div>
          <NavLink to="/laboratory">Laboratory</NavLink>
          <NavLink to="/pharmacy">Pharmacy</NavLink>

          <div className="nav-section">Finance</div>
          <NavLink to="/billing">Billing</NavLink>
          <NavLink to="/claims">Claims</NavLink>

          <div className="nav-section">Movement</div>
          <NavLink to="/referrals">Referrals</NavLink>
        </nav>
        <div className="sidebar-footer">
          <div className="muted small">{auth.username}</div>
          <div className="small">{auth.facilityName || "No facility"}</div>
          <button type="button" className="linkish" onClick={() => void auth.logout()}>Sign out</button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
