import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { KenyaFlag } from "../components/KenyaFlag";

export function PatientRegisterPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [afyaId, setAfyaId] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
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
    if (!firstName.trim() || !lastName.trim()) {
      setError("First and last name are required.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await auth.patientRegister({
        afya_id: afyaId.trim(),
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        phone: phone.trim() || undefined,
        email: email.trim() || undefined,
      });
      navigate("/portal", { replace: true });
    } catch (err) {
      const code = err instanceof ApiError ? err.code : "";
      const messages: Record<string, string> = {
        ACCOUNT_ALREADY_EXISTS: "An account already exists for this Afya ID. Please sign in.",
        NAME_REQUIRED_FOR_NEW_ACCOUNT: "First and last name are required for a new account.",
        USERNAME_CONFLICT: "This username is already in use. Try a different Afya ID.",
        INVALID_AFYA_ID: "Please enter a valid Afya ID (at least 3 characters).",
      };
      setError(
        messages[code] ||
          (err instanceof ApiError ? err.message || err.code : "Unable to create account."),
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
            Choose an Afya ID and password. If you already have an Afya ID from a hospital, use that
            same ID.
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
            placeholder="e.g. AFYA-YOURNAME"
          />
        </label>
        <label htmlFor="first_name">
          First name
          <input
            id="first_name"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            required
            autoComplete="given-name"
          />
        </label>
        <label htmlFor="last_name">
          Last name
          <input
            id="last_name"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            required
            autoComplete="family-name"
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

        <button
          type="submit"
          disabled={
            submitting || !afyaId.trim() || !password || !firstName.trim() || !lastName.trim()
          }
        >
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
