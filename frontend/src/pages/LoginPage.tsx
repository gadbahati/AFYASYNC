import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { getRememberedUsername, isRememberMeEnabled, setRememberMe } from "../auth/storage";
import { KenyaFlag } from "../components/KenyaFlag";

export function LoginPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState(getRememberedUsername() ?? "");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(isRememberMeEnabled());
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!auth.ready) {
    return <div className="auth-page"><div className="card auth-card"><p className="muted">Checking your secure session…</p></div></div>;
  }

  if (auth.username && auth.facilityId) return <Navigate to="/" replace />;
  if (auth.pendingFacilities) return <Navigate to="/select-facility" replace />;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const user = username.trim();
    if (!user || !password) return;
    setError(null);
    setSubmitting(true);
    try {
      setRememberMe(remember, user);
      const result = await auth.login(user, password);
      navigate(result === "select_facility" ? "/select-facility" : "/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "Unable to sign in. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page" aria-label="AfyaSync staff sign in">
      <form className="card auth-card" onSubmit={onSubmit} noValidate>
        <div className="auth-brand">
          <KenyaFlag />
          <div>
            <div className="brand-kicker">Republic of Kenya</div>
            <h1>AfyaSync</h1>
          </div>
        </div>
        <div>
          <h2>Facility / Staff sign in</h2>
          <p className="muted">Access your secure healthcare workspace.</p>
        </div>

        <label htmlFor="username">
          Username
          <input id="username" name="username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoCapitalize="none" spellCheck={false} required placeholder="Enter your username" />
        </label>
        <label htmlFor="password">
          Password
          <input id="password" name="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required placeholder="Enter your password" />
        </label>
        <label className="remember-row">
          <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
          <span>Remember my username on this device</span>
        </label>
        {error && <div className="error" role="alert">{error}</div>}
        <button type="submit" disabled={submitting || !username.trim() || !password}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
        <p className="muted small" style={{ marginTop: "1rem" }}>
          <Link to="/login">Not staff? Choose Patient sign in</Link>
        </p>
        <p className="muted small auth-note">Your password is sent only to the AfyaSync API. Session credentials are kept in temporary browser storage.</p>
      </form>
    </main>
  );
}
