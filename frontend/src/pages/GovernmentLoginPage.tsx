import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { getRememberedUsername, isRememberMeEnabled, setRememberMe } from "../auth/storage";
import { KenyaFlag } from "../components/KenyaFlag";

export function GovernmentLoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState(getRememberedUsername() ?? "");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(isRememberMeEnabled());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [mfaCode, setMfaCode] = useState("");
  const [mfaError, setMfaError] = useState<string | null>(null);

  if (!auth.ready) return <div className="auth-page"><div className="card auth-card"><p className="muted">Checking your secure session…</p></div></div>;
  if (auth.portalType === "government" && auth.username && auth.organizationId && !auth.pendingGovernmentOrganizations) return <Navigate to="/government" replace />;

  useEffect(() => {
    if (auth.ready && auth.portalType === "government" && auth.username && !auth.organizationId && !auth.pendingGovernmentMFA && !auth.pendingGovernmentOrganizations && !auth.governmentMFASetup) {
      auth.setupGovernmentMFA().catch(() => setMfaError("Unable to start MFA enrollment. Please contact your Government Portal administrator."));
    }
  }, [auth.ready, auth.portalType, auth.username, auth.organizationId, auth.pendingGovernmentMFA, auth.pendingGovernmentOrganizations, auth.governmentMFASetup]);

  async function submitMFA(event: FormEvent) {
    event.preventDefault();
    setMfaError(null);
    try {
      const result = await auth.verifyGovernmentMFA(mfaCode.trim());
      navigate(result === "select_organization" ? "/login/government" : "/government", { replace: true });
    } catch (err) {
      setMfaError(err instanceof ApiError ? err.message || err.code : "Invalid MFA code.");
    }
  }

  async function confirmSetup(event: FormEvent) {
    event.preventDefault();
    setMfaError(null);
    try {
      const result = await auth.confirmGovernmentMFASetup(mfaCode.trim());
      navigate(result === "select_organization" ? "/login/government" : "/government", { replace: true });
    } catch (err) {
      setMfaError(err instanceof ApiError ? err.message || err.code : "Invalid MFA code.");
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      setRememberMe(remember, username.trim());
      const result = await auth.governmentLogin(username.trim(), password);
      navigate(result === "select_organization" ? "/login/government" : "/government", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Unable to sign in to the Government Portal.");
    } finally {
      setBusy(false);
    }
  }

  if (auth.pendingGovernmentMFA) {
    return <main className="auth-page"><form className="card auth-card" onSubmit={submitMFA}>
      <div className="auth-brand"><KenyaFlag /><div><div className="brand-kicker">Republic of Kenya</div><h1>AfyaSync</h1></div></div>
      <h2>Multi-factor authentication</h2>
      <p className="muted">Enter the six-digit code from your authenticator application.</p>
      <label>Authenticator code<input inputMode="numeric" autoComplete="one-time-code" value={mfaCode} onChange={e=>setMfaCode(e.target.value.replace(/\D/g,"").slice(0,6))} required /></label>
      {mfaError && <div className="error" role="alert">{mfaError}</div>}
      <button type="submit" disabled={mfaCode.length !== 6}>Verify and continue</button>
    </form></main>;
  }

  if (auth.portalType === "government" && auth.username && !auth.organizationId && auth.governmentMFASetup) {
    return <main className="auth-page"><form className="card auth-card" onSubmit={confirmSetup}>
      <div className="auth-brand"><KenyaFlag /><div><div className="brand-kicker">Republic of Kenya</div><h1>AfyaSync</h1></div></div>
      <h2>Set up Government MFA</h2>
      <p className="muted">Add this account to an authenticator app. The secret is shown once so the government officer can enroll their own device.</p>
      <label>Setup secret<input readOnly value={auth.governmentMFASetup.secret} /></label>
      <label>Authenticator code<input inputMode="numeric" autoComplete="one-time-code" value={mfaCode} onChange={e=>setMfaCode(e.target.value.replace(/\D/g,"").slice(0,6))} required /></label>
      <p className="muted small">If your authenticator supports it, use this enrollment URI: {auth.governmentMFASetup.otpauth_uri}</p>
      {mfaError && <div className="error" role="alert">{mfaError}</div>}
      <button type="submit" disabled={mfaCode.length !== 6}>Confirm MFA enrollment</button>
    </form></main>;
  }

  if (auth.pendingGovernmentOrganizations) {
    return <main className="auth-page" aria-label="Government organization selection">
      <section className="card auth-card">
        <div className="auth-brand"><KenyaFlag /><div><div className="brand-kicker">Republic of Kenya</div><h1>AfyaSync</h1></div></div>
        <h2>Select government organization</h2>
        <p className="muted">Your identity has authenticated, but your government organization must be selected explicitly.</p>
        <div style={{display:"grid",gap:10}}>
          {auth.pendingGovernmentOrganizations.map(org => (
            <button key={org.organization_id} type="button" onClick={() => auth.selectGovernmentOrganization(org).then(() => navigate("/government", {replace:true})).catch((err:any) => setError(err?.message || err?.code || "ORGANIZATION_ACCESS_DENIED"))} style={{textAlign:"left",padding:16,border:"1px solid #cbd5e1",borderRadius:10,background:"#fff",cursor:"pointer"}}>
              <strong>{org.organization_name}</strong>
              <span className="muted small" style={{display:"block",marginTop:4}}>{org.organization_type.replaceAll("_"," ")} · {org.role_code} · {org.scope_level}</span>
            </button>
          ))}
        </div>
        {error && <div className="error" role="alert">{error}</div>}
      </section>
    </main>;
  }

  return <main className="auth-page" aria-label="Government Portal sign in">
    <form className="card auth-card" onSubmit={submit}>
      <div className="auth-brand"><KenyaFlag /><div><div className="brand-kicker">Republic of Kenya</div><h1>AfyaSync</h1></div></div>
      <div><h2>Government Portal</h2><p className="muted">County and national health administration, reporting and governed intelligence.</p></div>
      <label>Government username<input value={username} onChange={e=>setUsername(e.target.value)} autoComplete="username" required /></label>
      <label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password" required /></label>
      <label className="remember-row"><input type="checkbox" checked={remember} onChange={e=>setRemember(e.target.checked)} /><span>Remember my username on this device</span></label>
      {error && <div className="error" role="alert">{error}</div>}
      <button type="submit" disabled={busy || !username.trim() || !password}>{busy ? "Signing in…" : "Sign in to Government Portal"}</button>
      <p className="muted small" style={{marginTop:"1rem"}}><a href="/login">Back to portal selection</a></p>
    </form>
  </main>;
}
