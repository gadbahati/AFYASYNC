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
            <span className="muted">National health console</span>
          </div>
        </div>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/patients">Patients</NavLink>
          <NavLink to="/patients/new">Register patient</NavLink>
        </nav>
        <div className="sidebar-footer">
          <div className="muted small">{auth.username}</div>
          <div className="small">{auth.facilityName || "No facility"}</div>
          <button type="button" className="linkish" onClick={() => void auth.logout()}>
            Sign out
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
