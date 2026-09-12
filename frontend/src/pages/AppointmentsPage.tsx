import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Appointment } from "../api/types";

export function AppointmentsPage() {
  const [rows, setRows] = useState<Appointment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [patientId, setPatientId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [providerId, setProviderId] = useState("");
  const [date, setDate] = useState("2026-09-20T10:00");
  const [reason, setReason] = useState("Doctor follow-up");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  function load() {
    setLoading(true); setError(null);
    api.listAppointments().then(setRows).catch((err) => setError(err instanceof ApiError ? err.code : "LOAD_FAILED")).finally(() => setLoading(false));
  }
  useEffect(() => { load(); }, []);
  async function book() {
    if (!patientId.trim() || !departmentId.trim() || !date) { setNotice("Patient ID, department ID and return date/time are required."); return; }
    setSaving(true); setNotice(null);
    try {
      const appointment = await api.createAppointment({ patient_id: patientId.trim(), department_id: departmentId.trim(), provider_id: providerId.trim() || null, appointment_at: new Date(date).toISOString(), reason });
      setRows((current) => [...current, appointment].sort((a, b) => a.appointment_at.localeCompare(b.appointment_at)));
      setNotice(`Appointment booked for ${new Date(appointment.appointment_at).toLocaleString()}.`);
    } catch (err) { setNotice(err instanceof ApiError ? err.code : "BOOKING_FAILED"); }
    finally { setSaving(false); }
  }
  return <section className="page-stack">
    <header className="page-heading"><div><p className="eyebrow">Continuity of care</p><h1>Appointments & return visits</h1><p className="muted">Book a doctor, schedule a patient to return on another day, and keep the future visit attached to the facility.</p></div></header>
    <article className="card"><h2>Book a future visit</h2><div className="form-grid"><label>Patient ID<input value={patientId} onChange={(e) => setPatientId(e.target.value)} placeholder="Patient UUID" /></label><label>Department ID<input value={departmentId} onChange={(e) => setDepartmentId(e.target.value)} placeholder="Department UUID" /></label><label>Doctor / provider ID (optional)<input value={providerId} onChange={(e) => setProviderId(e.target.value)} placeholder="Provider UUID" /></label><label>Return date & time<input type="datetime-local" value={date} onChange={(e) => setDate(e.target.value)} /></label><label className="span-2">Reason / visit type<input value={reason} onChange={(e) => setReason(e.target.value)} /></label></div><div className="form-actions"><button onClick={book} disabled={saving}>{saving ? "Booking…" : "Book appointment"}</button>{notice && <span className="status-pill">{notice}</span>}</div></article>
    {loading && <p>Loading…</p>}{error && <div className="error">{error}</div>}
    {!loading && !error && <div className="table-wrap"><table><thead><tr><th>Date & time</th><th>Patient</th><th>Department</th><th>Doctor</th><th>Reason</th><th>Status</th></tr></thead><tbody>{rows.map((a) => <tr key={a.id}><td>{new Date(a.appointment_at).toLocaleString()}</td><td>{a.patient_id}</td><td>{a.department_id}</td><td>{a.provider_id || "Any available doctor"}</td><td>{a.reason || "Return visit"}</td><td><span className="status-pill">{a.status}</span></td></tr>)}{rows.length === 0 && <tr><td colSpan={6} className="muted">No appointments yet for this facility.</td></tr>}</tbody></table></div>}
  </section>;
}
