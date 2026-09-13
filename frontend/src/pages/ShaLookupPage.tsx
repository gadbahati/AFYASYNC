import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { SHAMember } from "../api/types";

/**
 * SHA path: lookup by membership number the way staff expect SHA to work.
 * Does NOT force AfyaSync membership enrollment.
 */
export function ShaLookupPage() {
  const navigate = useNavigate();
  const [membership, setMembership] = useState("");
  const [result, setResult] = useState<SHAMember | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    const value = membership.trim();
    if (value.length < 3) {
      setError("Enter a valid SHA membership number");
      return;
    }
    setBusy(true);
    try {
      const member = await api.verifyShaMember(value);
      setResult(member);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "SHA_LOOKUP_FAILED");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <Link to="/patients" className="muted">← Patients</Link>
          <h1>SHA member lookup</h1>
          <p className="muted">
            Patient already has SHA? Look them up by membership number. AfyaSync runs the facility record;
            SHA is only the coverage. No AfyaSync membership is required.
          </p>
        </div>
        <Link className="button secondary" to="/patients/new">No SHA — register patient</Link>
      </header>

      <form className="card form-grid" onSubmit={onSubmit}>
        <label className="full">
          SHA membership number
          <input
            value={membership}
            onChange={(e) => setMembership(e.target.value)}
            placeholder="Enter SHA / SHIF member number"
            autoFocus
          />
        </label>
        {error && <div className="error full">{error}</div>}
        <div className="full actions">
          <button type="submit" disabled={busy}>{busy ? "Looking up…" : "Look up SHA member"}</button>
        </div>
      </form>

      {result && (
        <section className="card" style={{ marginTop: 16 }}>
          <h2>{result.full_name}</h2>
          <p className="muted">Afya ID {result.afya_id} · Membership {result.membership_number}</p>
          <p>
            Coverage: <strong>{result.coverage_status}</strong>
            {result.date_of_birth ? ` · DOB ${result.date_of_birth}` : ""}
            {result.sex ? ` · ${result.sex}` : ""}
          </p>
          {result.benefit_package_codes?.length > 0 && (
            <p className="muted">Packages: {result.benefit_package_codes.join(", ")}</p>
          )}
          <div className="actions" style={{ marginTop: 12 }}>
            <button type="button" onClick={() => navigate(`/patients/${result.person_id}`)}>
              Open patient record
            </button>
            <button
              type="button"
              className="button secondary"
              onClick={() => navigate(`/patients/${result.person_id}/encounters/new`)}
            >
              Open encounter (SHA cover)
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
