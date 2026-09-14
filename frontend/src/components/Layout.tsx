import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "./KenyaFlag";

const navGroups = [
  { label: "Overview", links: [["/", "Dashboard"], ["/command-centre", "Command centre"], ["/national-command-centre", "National command centre"], ["/national-intelligence", "National intelligence"], ["/national-identity", "National identity"], ["/national-facilities", "Facility network"], ["/national-staff", "Staff network"], ["/national-payers", "Payer network"], ["/national-benefits", "Benefit configuration"], ["/national-supply", "Medicine supply"], ["/national-supply/planning", "Supply planning"], ["/national/referrals", "Referral network"], ["/coverage-simulator", "Coverage simulator"]] },
  { label: "Patients & care", links: [["/patients", "Patient register"], ["/patients/new", "Register patient"], ["/patients/sha-lookup", "Coverage lookup"], ["/coverage/sha-eligibility", "SHA eligibility verification"], ["/appointments", "Appointments"], ["/queue", "Clinical queue"], ["/referrals", "Referrals"]] },
  { label: "Clinical services", links: [["/laboratory", "Laboratory"], ["/pharmacy", "Pharmacy"], ["/benefits", "Benefit packages"]] },
  { label: "Revenue & financing", links: [["/billing", "Billing"], ["/claims", "Claims & rework"], ["/integrations", "Integration operations"]] },
] as const;

export function Layout() {
  const auth = useAuth();
  return <div className="app-shell">
    <aside className="sidebar" aria-label="Primary navigation">
      <div className="brand brand-row"><KenyaFlag /><div><strong>AfyaSync</strong><span className="muted">Health platform</span></div></div>
      <div className="facility-context"><span className="facility-context-label">Current facility</span><strong>{auth.facilityName || "No facility selected"}</strong></div>
      <nav>{navGroups.map((group) => <div className="nav-group" key={group.label}><div className="nav-section">{group.label}</div>{group.links.map(([to, label]) => <NavLink key={to} to={to} end={to === "/"}><span className="nav-dot" aria-hidden="true" />{label}</NavLink>)}</div>)}</nav>
      <div className="sidebar-footer"><div className="user-context"><span className="user-avatar" aria-hidden="true">{(auth.username || "U").slice(0, 1).toUpperCase()}</span><div><strong>{auth.username || "Staff user"}</strong><span className="muted small">Authenticated staff</span></div></div><button type="button" className="linkish signout" onClick={() => void auth.logout()}>Sign out</button></div>
    </aside>
    <main className="content"><header className="topbar"><div><span className="topbar-kicker">AfyaSync national health platform</span><span className="topbar-title">Facility operations</span></div><div className="topbar-context">{auth.facilityName || "Facility workspace"}</div></header><div className="content-inner"><Outlet /></div></main>
  </div>;
}
