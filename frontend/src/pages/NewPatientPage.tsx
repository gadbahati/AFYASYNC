import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";

export function NewPatientPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    first_name: "",
    middle_name: "",
    last_name: "",
    date_of_birth: "",
    sex: "",
    phone: "",
    email: "",
    address: "",
  });

  function update<K extends keyof typeof form>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await api.createPatient({
        first_name: form.first_name.trim(),
        middle_name: form.middle_name.trim() || null,
        last_name: form.last_name.trim(),
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
          <p className="muted">Creates identity and enrolls the patient at your current facility.</p>
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

        {error && <div className="error full">{error}</div>}

        <div className="full actions">
          <button type="submit" disabled={submitting}>{submitting ? "Saving…" : "Create patient"}</button>
        </div>
      </form>
    </div>
  );
}
