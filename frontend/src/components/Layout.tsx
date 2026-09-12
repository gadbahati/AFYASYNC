import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "./KenyaFlag";

export function Layout() {
  const auth = useAuth();
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand brand-row"><KenyaFlag /><div><strong>AfyaSync</strong><span className="muted">Staff console</span></div></div>
        <nav>
          <div className="nav-section">Overview</div><NavLink to="/" end>Dashboard</NavLink>
          <div className="nav-section">Patients</div><NavLink to="/patients">Patient register</NavLink><NavLink to="/patients/new">Register patient</NavLink>
          <div className="nav-section">Clinical</div><NavLink to="/appointments">Appointments</NavLink><NavLink to="/queue">Queue</NavLink><NavLink to="/sha-workflow">SHA care workflow</NavLink><NavLink to="/benefits">SHA benefits</NavLink>
          <div className="nav-section">Laboratory</div>
          <NavLink to="/laboratory">Laboratory workflow</NavLink>
          <div className="nav-subitem">• Order / add tests</div><div className="nav-subitem">• Record individual results</div><div className="nav-subitem">• Test-by-test pricing</div><div className="nav-subitem">• Forward to prescription</div>
          <NavLink to="/pharmacy">Pharmacy</NavLink>
          <div className="nav-section">Finance</div><NavLink to="/billing">Billing</NavLink><NavLink to="/claims">Claims</NavLink>
          <div className="nav-section">Movement</div><NavLink to="/referrals">Referrals</NavLink>
        </nav>
        <div className="sidebar-footer"><div className="muted small">{auth.username}</div><div className="small">{auth.facilityName || "No facility"}</div><button type="button" className="linkish" onClick={() => void auth.logout()}>Sign out</button></div>
      </aside>
      <main className="content">{auth.demoMode && <div className="demo-banner">Demo mode: sample data only. Not connected to the live API.</div>}<Outlet /></main>
    </div>
  );
}
