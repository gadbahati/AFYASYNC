import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useWorkspace, type ContextScope } from "../workspaces/WorkspaceContext";
import { WORKSPACES } from "../workspaces/workspaces";

type NavLinkItem = readonly [string, string];
type NavGroup = { label: string; links: readonly NavLinkItem[] };

const SCOPE_OPTIONS: { value: ContextScope; label: string }[] = [
  { value: "facility", label: "Facility" },
  { value: "network", label: "Network" },
  { value: "county", label: "County" },
  { value: "national", label: "National" },
];

const navGroups: readonly NavGroup[] = [
  {
    label: "Overview",
    links: [
      ["/", "Dashboard"],
      ["/command-centre", "Command centre"],
      ["/national-command-centre", "National command centre"],
      ["/national-intelligence", "National intelligence"],
      ["/national-identity", "National identity"],
      ["/national-facilities", "Facility network"],
      ["/national-staff", "Staff network"],
      ["/national-payers", "Payer network"],
      ["/national-benefits", "Benefit configuration"],
      ["/national-financing", "Financing exchange"],
      ["/eligibility", "Eligibility engine"],
      ["/universal-identity", "Universal identity"],
      ["/financing-preauthorization", "Preauthorization exchange"],
      ["/adjudication", "Claims adjudication"],
      ["/settlements", "Settlement & provider payments"],
      ["/fraud-integrity", "Fraud, waste & abuse"],
      ["/financing-wallet", "Patient financing wallet"],
      ["/provider-network", "Provider network"],
      ["/health-exchange", "National health exchange"],
      ["/care-coordination", "Care coordination"],
      ["/referral-routing", "Intelligent referral routing"],
      ["/referral-booking", "Referral decision & booking"],
      ["/benefit-engine", "Benefits & tariff engine"],
      ["/national-supply", "Medicine supply"],
      ["/national/supply/planning", "Supply planning"],
      ["/national/referrals", "Referral network"],
      ["/national/capacity", "Clinical capacity"],
      ["/coverage-simulator", "Coverage simulator"],
    ],
  },
  {
    label: "Patients & care",
    links: [
      ["/patients", "Patient register"],
      ["/household-wallet", "Household health wallet"],
      ["/patients/new", "Register patient"],
      ["/patients/sha-lookup", "Coverage lookup"],
      ["/continuity-scan", "Continuity card scan"],
      ["/offline-clinic", "Offline clinic"],
      ["/coverage/sha-eligibility", "SHA eligibility verification"],
      ["/appointments", "Appointments"],
      ["/messages", "Messages"],
      ["/treat-abroad", "Treat Abroad"],
      ["/queue", "Clinical queue"],
      ["/referrals", "Referrals"],
    ],
  },
  {
    label: "Clinical services",
    links: [
      ["/mch", "Maternal & child health"],
      ["/laboratory", "Laboratory"],
      ["/pharmacy", "Pharmacy"],
      ["/benefits", "Benefit packages"],
    ],
  },
  {
    label: "Revenue intelligence",
    links: [
      ["/benefit-engine", "Benefits & tariff engine"],
      ["/claims-clearinghouse", "Claims clearinghouse"],
      ["/revenue-recovery", "Revenue recovery"],
      ["/revenue-anomalies", "Revenue anomaly intelligence"],
      ["/financial-command-centre", "Financial command centre"],
      ["/collection-work", "Collection work queue"],
      ["/revenue-resolution", "Revenue resolution"],
      ["/denial-appeals", "Denial & appeal operations"],
      ["/payer-command", "Payer command centre"],
      ["/tariff-intelligence", "Tariff intelligence"],
      ["/contract-renewal", "Contract renewal"],
      ["/payer-negotiation", "Payer negotiation"],
      ["/contract-execution", "Contract approval & execution"],
      ["/contract-activation", "Contract activation"],
      ["/contract-guardrails", "Contract compliance guardrails"],
      ["/contract-cash-command", "Contract-to-cash command centre"],
      ["/payer-contract-cash", "Payer contract-to-cash"],
      ["/leakage-intelligence", "Revenue leakage intelligence"],
      ["/recovery-cash-conversion", "Recovery & cash conversion"],
      ["/executive-revenue", "Executive revenue command centre"],
      ["/revenue-control-tower", "Revenue control tower"],
      ["/revenue-action-priorities", "Revenue action priorities"],
      ["/revenue-workflow-automation", "Revenue workflow automation"],
      ["/cash-closure-command", "Cash closure command centre"],
      ["/revenue-cash-assurance", "Revenue & cash assurance"],
    ],
  },
  {
    label: "Revenue & reporting",
    links: [
      ["/billing", "Billing"],
      ["/claims", "Claims & rework"],
      ["/reports", "Daily & monthly reports"],
      ["/integrations", "Integration operations"],
      ["/security-operations", "Security operations"],
      ["/workforce", "Workforce & credentials"],
      ["/onboarding", "Onboarding & migration"],
      ["/training", "Training & help"],
      ["/rollout", "County rollout & evidence"],
      ["/warehouse", "Analytics warehouse"],
      ["/certification", "DHA certification"],
      ["/production", "Production readiness"],
      ["/observability", "Observability & SLOs"],
      ["/retention", "Retention & erasure"],
      ["/partner-sandbox", "Partner sandbox"],
      ["/disaster-recovery", "Disaster recovery"],
      ["/change-control", "Change control"],
      ["/pilot-handover", "Pilot handover"],
      ["/performance", "Performance acceptance"],
      ["/risk-register", "Residual risk register"],
      ["/national-readiness", "National readiness"],
    ],
  },
] as const;

const KENYA_CREST =
  "https://upload.wikimedia.org/wikipedia/commons/f/f6/Coat_of_arms_of_Kenya_%28Official%29.svg";

function KenyaCrest({ className = "" }: { className?: string }) {
  return <img className={`kenya-crest ${className}`} src={KENYA_CREST} alt="Coat of arms of Kenya" />;
}

export function Layout() {
  const auth = useAuth();
  const { workspace, setWorkspace, scope, setScope } = useWorkspace();
  const activeWorkspace = WORKSPACES.find((item) => item.id === workspace) || WORKSPACES[0];
  const [availableScopes, setAvailableScopes] = useState<ContextScope[]>(["facility"]);

  useEffect(() => {
    let cancelled = false;
    api
      .contextOverview()
      .then((v: { available_scopes?: string[] }) => {
        if (cancelled) return;
        const scopes = (Array.isArray(v?.available_scopes) ? v.available_scopes : ["facility"]).filter(
          (s): s is ContextScope =>
            s === "facility" || s === "network" || s === "county" || s === "national",
        );
        setAvailableScopes(scopes.length ? scopes : ["facility"]);
        if (scopes.length && !scopes.includes(scope)) {
          setScope(scopes[0]);
        }
      })
      .catch(() => {
        if (!cancelled) setAvailableScopes(["facility"]);
      });
    return () => {
      cancelled = true;
    };
  }, [auth.facilityId]);

  const scopeLabel = SCOPE_OPTIONS.find((o) => o.value === scope)?.label || scope;

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand brand-row">
          <div className="brand-mark">
            <KenyaCrest />
          </div>
          <div className="brand-copy">
            <strong>AfyaSync</strong>
            <span>National health platform</span>
          </div>
        </div>
        <div className="institution-strip">
          <span>KENYA</span>
          <strong>Healthcare, connected.</strong>
        </div>
        <div className="facility-context">
          <span className="facility-context-label">CURRENT FACILITY</span>
          <strong>{auth.facilityName || "No facility selected"}</strong>
        </div>

        <div
          className="scope-switcher"
          style={{ padding: "12px 10px", borderBottom: "1px solid rgba(148,163,184,.25)" }}
        >
          <div className="nav-section" style={{ marginBottom: 8 }}>
            OPERATING SCOPE
          </div>
          <select
            aria-label="Choose operating scope"
            value={scope}
            onChange={(e) => setScope(e.target.value as ContextScope)}
            style={{
              width: "100%",
              padding: "9px 10px",
              borderRadius: 9,
              border: "1px solid #cbd5e1",
              background: "#fff",
              cursor: "pointer",
            }}
          >
            {SCOPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value} disabled={!availableScopes.includes(opt.value)}>
                {opt.label}
                {!availableScopes.includes(opt.value) ? " — restricted" : ""}
              </option>
            ))}
          </select>
          <p className="muted small" style={{ margin: "8px 0 0" }}>
            Lists and aggregates use this scope. Writes stay on your facility.
          </p>
        </div>

        <div
          className="workspace-switcher"
          style={{ padding: "12px 10px", borderBottom: "1px solid rgba(148,163,184,.25)" }}
        >
          <div className="nav-section" style={{ marginBottom: 8 }}>
            WORKSPACE
          </div>
          <select
            aria-label="Choose workspace"
            value={workspace}
            onChange={(e) => setWorkspace(e.target.value as typeof workspace)}
            style={{ width: "100%", padding: "9px 10px", borderRadius: 9 }}
          >
            {WORKSPACES.map((item) => (
              <option key={item.id} value={item.id}>
                {item.icon} {item.label}
              </option>
            ))}
          </select>
          <NavLink to="/workspace" style={{ marginTop: 8 }}>
            <span className="nav-dot" aria-hidden="true" />
            Open {activeWorkspace.label}
          </NavLink>
        </div>

        <nav>
          <div className="nav-group">
            <div className="nav-section">
              {activeWorkspace.icon} {activeWorkspace.label}
            </div>
            {activeWorkspace.links.map(([to, label]) => (
              <NavLink key={to} to={to} end={to === "/"}>
                <span className="nav-dot" aria-hidden="true" />
                {label}
              </NavLink>
            ))}
          </div>
          <details className="nav-group">
            <summary className="nav-section" style={{ cursor: "pointer" }}>
              All modules
            </summary>
            {navGroups.map((group) => (
              <div key={group.label}>
                <div className="nav-section">{group.label}</div>
                {group.links.map(([to, label]) => (
                  <NavLink key={to} to={to} end={to === "/"}>
                    <span className="nav-dot" aria-hidden="true" />
                    {label}
                  </NavLink>
                ))}
              </div>
            ))}
          </details>
        </nav>

        <div className="sidebar-footer">
          <div className="user-context">
            <span className="user-avatar" aria-hidden="true">
              {(auth.username || "U").slice(0, 1).toUpperCase()}
            </span>
            <div>
              <strong>{auth.username || "Staff user"}</strong>
              <span className="muted small">Authenticated staff</span>
            </div>
          </div>
          <button type="button" className="linkish signout" onClick={() => void auth.logout()}>
            Sign out
          </button>
        </div>
      </aside>

      <main className="content">
        <header className="topbar">
          <div className="topbar-brand">
            <KenyaCrest className="topbar-crest" />
            <div>
              <span className="topbar-kicker">REPUBLIC OF KENYA • HEALTHCARE OPERATIONS</span>
              <span className="topbar-title">AfyaSync</span>
            </div>
          </div>
          <div className="topbar-context" style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <span className="status-dot" />
            <span>{auth.facilityName || "Facility workspace"}</span>
            <span
              className="status-pill"
              title="Operating scope for lists and aggregates"
              style={{
                background: "#0f766e",
                color: "#fff",
                padding: "4px 10px",
                borderRadius: 999,
                fontSize: 12,
                fontWeight: 600,
                letterSpacing: "0.02em",
              }}
            >
              SCOPE: {scopeLabel.toUpperCase()}
            </span>
          </div>
        </header>
        <div className="content-inner">
          <Outlet />
        </div>
        <footer className="site-footer">
          <div className="footer-main">
            <div className="footer-identity">
              <KenyaCrest className="footer-crest" />
              <div>
                <strong>AfyaSync</strong>
                <span>Healthcare, connected.</span>
                <small>Kenya health information infrastructure</small>
              </div>
            </div>
            <div className="footer-links">
              <strong>PLATFORM</strong>
              <span>Secure health operations</span>
              <span>Interoperable services</span>
              <span>Patient-centred care</span>
            </div>
            <div className="footer-links">
              <strong>GOVERNANCE</strong>
              <span>Authorised users only</span>
              <span>Audit-ready operations</span>
              <span>Privacy & security by design</span>
            </div>
          </div>
          <div className="footer-bottom">
            <div className="footer-copyright">
              <span>
                © {new Date().getFullYear()} AfyaSync. Developed by <strong>BAHATI GAD WANGWE</strong>. All rights
                reserved.
              </span>
              <span>
                Unauthorized copying, reverse engineering, redistribution or commercial use is strictly prohibited and
                will be prosecuted under Kenyan and international law.
              </span>
              <span>AfyaSync is an independent health technology platform and is not the Government of Kenya.</span>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
