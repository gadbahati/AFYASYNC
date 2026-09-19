import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

export function PatientRegisterPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [afyaId, setAfyaId] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await auth.patientRegister({
        afya_id: afyaId.trim(),
        password,
        phone: phone.trim() || undefined,
        email: email.trim() || undefined,
      });
      navigate("/portal", { replace: true });
    } catch (err) {
      const code = err instanceof ApiError ? err.code : "";
      const messages: Record<string, string> = {
        AFYA_ID_NOT_FOUND:
          "This Afya ID was not found. You must first be registered as a patient at a facility.",
        ACCOUNT_ALREADY_EXISTS: "An account already exists for this Afya ID. Please sign in.",
      };
      setError(
        messages[code] ||
          (err instanceof ApiError ? err.message || err.code : "Unable to create account.")
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page" aria-label="Create patient account">
      <form className="card auth-card" onSubmit={onSubmit} noValidate>
        <div className="auth-brand">
          <KenyaFlag />
          <div>
            <div className="brand-kicker">Republic of Kenya</div>
            <h1>AfyaSync</h1>
          </div>
        </div>
        <div>
          <h2>Create patient account</h2>
          <p className="muted">
            You need an existing Afya ID from a hospital registration. This only sets your portal
            password.
          </p>
        </div>

        <label htmlFor="afya_id">
          Afya ID
          <input
            id="afya_id"
            value={afyaId}
            onChange={(e) => setAfyaId(e.target.value)}
            required
            autoCapitalize="none"
            spellCheck={false}
            placeholder="Your Afya ID"
          />
        </label>
        <label htmlFor="password">
          Password (min 8 characters)
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>
        <label htmlFor="confirm">
          Confirm password
          <input
            id="confirm"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>
        <label htmlFor="phone">
          Phone (optional, for password reset)
          <input
            id="phone"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            autoComplete="tel"
            placeholder="07…"
          />
        </label>
        <label htmlFor="email">
          Email (optional, for password reset)
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
        </label>

        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}

        <button type="submit" disabled={submitting || !afyaId.trim() || !password}>
          {submitting ? "Creating account…" : "Create account & sign in"}
        </button>

        <p className="muted small" style={{ marginTop: "1rem" }}>
          <Link to="/login/patient">Already have an account? Sign in</Link>
          {" · "}
          <Link to="/login">Back</Link>
        </p>
      </form>
    </main>
  );
}
