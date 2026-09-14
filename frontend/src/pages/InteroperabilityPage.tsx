import { useState } from "react";
import { getFHIRPatient, type FHIRPatientResource } from "../api/interoperabilityApi";

export function InteroperabilityPage() {
  const [patientId, setPatientId] = useState("");
  const [patient, setPatient] = useState<FHIRPatientResource | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadPatient() {
    const value = patientId.trim();
    if (!value) { setError("Enter a patient ID."); return; }
    setLoading(true); setError(""); setPatient(null);
    try { setPatient(await getFHIRPatient(value)); }
    catch (err) { setError(err instanceof Error ? err.message : "INTEROPERABILITY_READ_FAILED"); }
    finally { setLoading(false); }
  }

  return <main className="page-content">
    <section className="page-header">
      <div><p className="eyebrow">Interoperability</p><h1>FHIR patient gateway</h1><p>Read the minimum necessary patient identity resource for the currently authorised facility.</p></div>
    </section>
    <section className="card">
      <div className="form-grid">
        <label>Patient ID<input value={patientId} onChange={(e) => setPatientId(e.target.value)} placeholder="Patient UUID" /></label>
        <button type="button" onClick={loadPatient} disabled={loading}>{loading ? "Reading…" : "Read patient"}</button>
      </div>
      {error && <p className="error-message">{error}</p>}
    </section>
    {patient && <section className="card">
      <p className="eyebrow">FHIR Patient</p>
      <h2>{patient.name[0]?.given?.join(" ")} {patient.name[0]?.family}</h2>
      <p>Afya ID: {patient.identifier[0]?.value ?? "—"}</p>
      <p>Date of birth: {patient.birthDate ?? "—"}</p>
      <p>Sex: {patient.gender ?? "—"}</p>
      <p>Status: {patient.active ? "Active" : "Inactive"}</p>
      <small>Interoperability access is facility-scoped and audited. National ID, contacts, address and clinical records are not included.</small>
    </section>}
  </main>;
}
