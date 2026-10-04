import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";

/**
 * Facility patient registration only.
 * Creating a patient record is NOT the same as AfyaSync insurance membership.
 * Coverage (AFYASYNC | SHA | CASH) is chosen when opening an encounter / attaching coverage.
 */
export function NewPatientPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [checkingMpi, setCheckingMpi] = useState(false);
  const [mpiCandidates, setMpiCandidates] = useState<any[]>([]);
  const [mpiChecked, setMpiChecked] = useState(false);
  const [form, setForm] = useState({
    first_name: "",
    middle_name: "",
    last_name: "",
    national_id_number: "",
    date_of_birth: "",
    sex: "",
    phone: "",
    email: "",
    address: "",
  });

  function update<K extends keyof typeof form>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function checkMpi() {
    setError(null);
    setCheckingMpi(true);
    try {
      const result = await api.mpiCandidates({
        first_name: form.first_name.trim() || undefined,
        last_name: form.last_name.trim() || undefined,
        date_of_birth: form.date_of_birth || undefined,
        phone: form.phone.trim() || undefined,
        national_id_number: form.national_id_number.trim() || undefined,
      }) as any;
      setMpiCandidates(result.candidates || []);
      setMpiChecked(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "MPI_CHECK_FAILED");
      setMpiCandidates([]);
      setMpiChecked(false);
    } finally {
      setCheckingMpi(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!/^\d{7,9}$/.test(form.national_id_number.trim())) {
      setError("Enter a valid 7–9 digit national ID number.");
      return;
    }
    if (!mpiChecked) {
      setError("Run the Master Patient Index check before registering this patient.");
      return;
    }
    if (mpiCandidates.length) {
      setError("A possible existing patient was found. Open the existing record or confirm the identity before creating another record.");
      return;
    }
    setSubmitting(true);
    try {
      const created = await api.createPatient({
        first_name: form.first_name.trim(),
        middle_name: form.middle_name.trim() || null,
        last_name: form.last_name.trim(),
        national_id_number: form.national_id_number.trim(),
        date_of_birth: form.date_of_birth || null,
        sex: form.sex || null,
        phone: form.phone.trim() || null,
        email: form.email.trim() || null,
        address: form.address.trim() || null,
      });
      navigate(`/patients/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.code : "CREATE_FAILED");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h1>Register patient</h1>
          <p className="muted">
            Creates a facility patient record and AfyaSync identity. This does not force SHA registration
            and does not enroll paid AfyaSync membership. Choose coverage when you open an encounter:
            AfyaSync membership, SHA (no AfyaSync membership required), or cash.
          </p>
        </div>
      </header>
      <form className="card form-grid" onSubmit={onSubmit}>
        <label>
          First name
          <input required value={form.first_name} onChange={(e) => update("first_name", e.target.value)} />
        </label>
        <label>
          Middle name
          <input value={form.middle_name} onChange={(e) => update("middle_name", e.target.value)} />
        </label>
        <label>
          Last name
          <input required value={form.last_name} onChange={(e) => update("last_name", e.target.value)} />
        </label>
        <label>
          National ID number
          <input
            required
            inputMode="numeric"
            pattern="[0-9]{7,9}"
            minLength={7}
            maxLength={9}
            value={form.national_id_number}
            onChange={(e) => update("national_id_number", e.target.value.replace(/\D/g, ""))}
            placeholder="7–9 digits"
          />
        </label>
        <label>
          Date of birth
          <input type="date" value={form.date_of_birth} onChange={(e) => update("date_of_birth", e.target.value)} />
        </label>
        <label>
          Sex
          <select value={form.sex} onChange={(e) => update("sex", e.target.value)}>
            <option value="">—</option>
            <option value="FEMALE">Female</option>
            <option value="MALE">Male</option>
            <option value="OTHER">Other</option>
          </select>
        </label>
        <label>
          Phone
          <input value={form.phone} onChange={(e) => update("phone", e.target.value)} />
        </label>
        <label>
          Email
          <input type="email" value={form.email} onChange={(e) => update("email", e.target.value)} />
        </label>
        <label className="full">
          Address
          <input value={form.address} onChange={(e) => update("address", e.target.value)} />
        </label>
        <div className="full card" style={{marginTop:8}}>
          <strong>Master Patient Index check</strong>
          <p className="muted small">Search existing facility identities before creating a new AfyaSync identity. A match must be reviewed instead of creating a duplicate.</p>
          <button type="button" className="button secondary" onClick={checkMpi} disabled={checkingMpi || !form.first_name.trim() && !form.last_name.trim() && !form.phone.trim() && !form.national_id_number.trim() && !form.date_of_birth}>
            {checkingMpi ? "Checking MPI…" : "Check existing patient"}
          </button>
          {mpiChecked && mpiCandidates.length === 0 && <p className="success">No existing candidate matched the supplied identifiers. Registration may continue.</p>}
          {mpiCandidates.length > 0 && <div className="error" style={{marginTop:10}}>
            <strong>Possible existing patient(s) found</strong>
            {mpiCandidates.map((candidate:any) => <div key={candidate.patient_id} style={{marginTop:8}}>
              <Link to={`/patients/${candidate.patient_id}/journey`}><strong>{candidate.afya_id}</strong> — {candidate.full_name}</Link>
              <div className="small muted">Match {candidate.match_score}% · {candidate.match_reasons.join(", ")}</div>
            </div>)}
          </div>}
        </div>
        <div className="muted full">
          National ID numbers remain hashed. MPI review happens before a new identity is created.
        </div>
        {error && <div className="error full">{error}</div>}
        <div className="full actions">
          <button type="submit" disabled={submitting}>{submitting ? "Saving…" : "Create patient"}</button>
        </div>
      </form>
    </div>
  );
}
