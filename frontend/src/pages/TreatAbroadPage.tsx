import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Procedure = {
  id: string;
  code: string;
  name: string;
  max_cover_kes?: number;
  description?: string | null;
};

type CaseRow = {
  id: string;
  case_number: string;
  patient_id: string;
  procedure_id: string;
  status: string;
  clinical_summary: string;
  local_unavailability_reason: string;
  foreign_hospital_name?: string | null;
  foreign_hospital_country?: string | null;
  sha_preauth_reference?: string | null;
  created_at: string;
};

type Patient = {
  id: string;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  afya_id?: string | null;
};

const NEXT: Record<string, string[]> = {
  DRAFT: ["SUBMITTED"],
  SUBMITTED: ["UNDER_REVIEW", "REJECTED"],
  UNDER_REVIEW: ["APPROVED", "REJECTED"],
  APPROVED: ["TRAVEL_ARRANGED", "REJECTED"],
  REJECTED: ["CLOSED"],
  TRAVEL_ARRANGED: ["TREATMENT_IN_PROGRESS"],
  TREATMENT_IN_PROGRESS: ["RETURNED"],
  RETURNED: ["CLOSED"],
  CLOSED: [],
};

export function TreatAbroadPage() {
  const auth = useAuth();
  const [procedures, setProcedures] = useState<Procedure[]>([]);
  const [cases, setCases] = useState<CaseRow[]>([]);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [patientId, setPatientId] = useState("");
  const [procedureId, setProcedureId] = useState("");
  const [summary, setSummary] = useState("");
  const [localReason, setLocalReason] = useState("");
  const [hospitalName, setHospitalName] = useState("");
  const [hospitalCountry, setHospitalCountry] = useState("");
  const [hospitalCity, setHospitalCity] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [procs, caseRows, patientRes] = await Promise.all([
        api.listTreatAbroadProcedures(),
        api.listTreatAbroadCases(),
        api.listPatients(100, 0),
      ]);
      setProcedures(Array.isArray(procs) ? procs : []);
      setCases(Array.isArray(caseRows) ? caseRows : []);
      setPatients(patientRes?.items || []);
    } catch (e) {
      setError(e instanceof ApiError ? e.message || e.code : "LOAD_FAILED");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function patientName(id: string) {
    const p = patients.find((x) => x.id === id);
    if (!p) return id.slice(0, 8);
    return [p.first_name, p.middle_name, p.last_name].filter(Boolean).join(" ");
  }

  function procedureName(id: string) {
    return procedures.find((p) => p.id === id)?.name || id.slice(0, 8);
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!auth.facilityId) {
      setError("Select a facility workspace first.");
      return;
    }
    if (!patientId || !procedureId || summary.trim().length < 20 || localReason.trim().length < 10) {
      setError("Patient, procedure, clinical summary (20+ chars) and local unavailability reason (10+ chars) are required.");
      return;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      // referring_clinician_id: use a stable placeholder UUID from me if needed — API requires UUID
      const me = await api.me();
      const clinicianId = me?.data?.id || me?.id;
      await api.createTreatAbroadCase({
        patient_id: patientId,
        facility_id: auth.facilityId,
        procedure_id: procedureId,
        clinical_summary: summary.trim(),
        local_unavailability_reason: localReason.trim(),
        referring_clinician_id: clinicianId,
        foreign_hospital_name: hospitalName || null,
        foreign_hospital_country: hospitalCountry || null,
        foreign_hospital_city: hospitalCity || null,
      });
      setNotice("Treat Abroad case created as DRAFT.");
      setSummary("");
      setLocalReason("");
      setHospitalName("");
      setHospitalCountry("");
      setHospitalCity("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "CREATE_FAILED");
    } finally {
      setSaving(false);
    }
  }

  async function advance(caseId: string, status: string) {
    setSaving(true);
    setError(null);
    try {
      await api.updateTreatAbroadCase(caseId, { status });
      setNotice(`Case moved to ${status}.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message || err.code : "UPDATE_FAILED");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="page-stack">
      <header className="page-heading">
        <div>
          <p className="eyebrow">SHA overseas care</p>
          <h1>Treat Abroad</h1>
          <p className="muted">
            Open and track SHA overseas treatment cases for procedures not available locally.
          </p>
        </div>
      </header>

      {error && <div className="error">{error}</div>}
      {notice && <div className="success-box">{notice}</div>}

      <article className="card">
        <h2>Open a new case</h2>
        <form className="form-grid" onSubmit={onCreate}>
          <label>
            Patient
            <select value={patientId} onChange={(e) => setPatientId(e.target.value)} required>
              <option value="">Select patient</option>
              {patients.map((p) => (
                <option key={p.id} value={p.id}>
                  {[p.first_name, p.last_name].filter(Boolean).join(" ")}
                  {p.afya_id ? ` · ${p.afya_id}` : ""}
                </option>
              ))}
            </select>
          </label>
          <label>
            Approved procedure
            <select value={procedureId} onChange={(e) => setProcedureId(e.target.value)} required>
              <option value="">Select procedure</option>
              {procedures.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.code})
                </option>
              ))}
            </select>
          </label>
          <label className="span-2">
            Clinical summary
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              rows={3}
              required
              minLength={20}
              placeholder="Why this patient needs overseas treatment (min 20 characters)"
            />
          </label>
          <label className="span-2">
            Why not available in Kenya
            <textarea
              value={localReason}
              onChange={(e) => setLocalReason(e.target.value)}
              rows={2}
              required
              minLength={10}
              placeholder="Local unavailability justification"
            />
          </label>
          <label>
            Foreign hospital (optional)
            <input value={hospitalName} onChange={(e) => setHospitalName(e.target.value)} />
          </label>
          <label>
            Country (optional)
            <input value={hospitalCountry} onChange={(e) => setHospitalCountry(e.target.value)} />
          </label>
          <label>
            City (optional)
            <input value={hospitalCity} onChange={(e) => setHospitalCity(e.target.value)} />
          </label>
          <div className="form-actions span-2">
            <button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Create case (DRAFT)"}
            </button>
          </div>
        </form>
      </article>

      <article className="card">
        <h2>Facility cases</h2>
        {loading ? (
          <p className="muted">Loading…</p>
        ) : cases.length === 0 ? (
          <p className="muted small">No Treat Abroad cases yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Patient</th>
                  <th>Procedure</th>
                  <th>Status</th>
                  <th>Hospital</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <strong>{c.case_number}</strong>
                      <div className="muted small">
                        {new Date(c.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td>{patientName(c.patient_id)}</td>
                    <td>{procedureName(c.procedure_id)}</td>
                    <td>
                      <span className="status-pill">{c.status}</span>
                    </td>
                    <td>
                      {c.foreign_hospital_name || "—"}
                      {c.foreign_hospital_country ? `, ${c.foreign_hospital_country}` : ""}
                    </td>
                    <td>
                      <div className="actions">
                        {(NEXT[c.status] || []).map((s) => (
                          <button
                            key={s}
                            type="button"
                            className="secondary"
                            disabled={saving}
                            onClick={() => void advance(c.id, s)}
                          >
                            → {s.replace(/_/g, " ")}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </section>
  );
}
