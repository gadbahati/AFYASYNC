import type {
  Admission, ApiErrorBody, Appointment, AuthMe, BenefitPackage, ClinicalTimeline, Consultation, Department,
  Diagnosis, Encounter, EncounterCreate, FacilityOption, FacilityReport, LoginResult, Patient, PatientCreate,
  PatientListResponse, PreAuthorization, Queue, QueueEntry, SHAMember, TokenResponse, Vital,
} from "./types";
import { demoClinicalTimeline, demoCreateEncounter, demoCreatePatient, demoDepartments, demoFacilityReport, demoGetPatient, demoListPatients } from "./demoData";
import { clearSession, getAccessToken, getRefreshToken, isDemoMode, setSession } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message?: string) { super(message || code); this.status = status; this.code = code; }
}
function parseDetail(body: ApiErrorBody | null): string {
  if (!body?.detail) return "REQUEST_FAILED";
  if (typeof body.detail === "string") return body.detail;
  return body.detail.code || body.detail.message || "REQUEST_FAILED";
}
let refreshPromise: Promise<boolean> | null = null;
async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: refresh }) });
    if (!res.ok) { clearSession(); return false; }
    const data = (await res.json()) as TokenResponse;
    setSession({ access_token: data.access_token, refresh_token: data.refresh_token });
    return true;
  } catch { clearSession(); return false; }
}
async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  if (!API_BASE && import.meta.env.PROD) throw new ApiError(0, "API_NOT_CONFIGURED", "VITE_API_BASE_URL is not set on this deployment. Point it at your AfyaSync API host.");
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res: Response;
  try { res = await fetch(`${API_BASE}${path}`, { ...init, headers }); }
  catch { throw new ApiError(0, "API_UNREACHABLE", "Cannot reach the AfyaSync API. Check that the backend is running and VITE_API_BASE_URL is correct."); }
  if (res.status === 401 && retry) {
    if (!refreshPromise) refreshPromise = tryRefresh().finally(() => { refreshPromise = null; });
    if (await refreshPromise) return request<T>(path, init, false);
  }
  if (!res.ok) {
    let body: ApiErrorBody | null = null;
    try { body = (await res.json()) as ApiErrorBody; } catch { body = null; }
    if (!body && (res.status === 404 || res.status === 405)) throw new ApiError(res.status, "API_UNREACHABLE", "API route not found. Set VITE_API_BASE_URL to your backend origin.");
    throw new ApiError(res.status, parseDetail(body));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const DEMO_APPOINTMENTS: Appointment[] = [{ id: "a1", patient_id: "p1", facility_id: "f1", department_id: "d1", provider_id: null, appointment_at: new Date().toISOString(), reason: "Follow-up", status: "BOOKED" }];
const DEMO_QUEUE_ENTRIES: QueueEntry[] = [{ id: "q1", queue_id: "queue1", patient_id: "p1", appointment_id: null, encounter_id: null, priority: "NORMAL", status: "WAITING", queued_at: new Date().toISOString(), called_at: null, completed_at: null }];

export const api = {
  login(username: string, password: string) { return request<LoginResult>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }, false); },
  selectFacility(facility_id: string) { return request<TokenResponse>("/api/v1/auth/select-facility", { method: "POST", body: JSON.stringify({ facility_id }) }, false); },
  facilities() { return request<FacilityOption[]>("/api/v1/auth/facilities"); },
  me() { if (isDemoMode()) return Promise.resolve({ success: true, data: { user_id: "demo", username: "demo.viewer", status: "ACTIVE" }, message: "Demo session" } satisfies AuthMe); return request<AuthMe>("/api/v1/auth/me"); },
  logout(refresh_token: string) { if (isDemoMode()) return Promise.resolve({ success: true }); return request<{ success: boolean }>("/api/v1/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token }) }, false); },
  listPatients(limit = 50, offset = 0) { if (isDemoMode()) return Promise.resolve(demoListPatients(limit, offset)); return request<PatientListResponse>(`/api/v1/patients?limit=${limit}&offset=${offset}`); },
  getPatient(id: string) { if (isDemoMode()) { try { return Promise.resolve(demoGetPatient(id)); } catch { return Promise.reject(new ApiError(404, "PATIENT_NOT_FOUND")); } } return request<Patient>(`/api/v1/patients/${id}`); },
  createPatient(payload: PatientCreate) { if (isDemoMode()) return Promise.resolve(demoCreatePatient(payload)); return request<Patient>("/api/v1/patients", { method: "POST", body: JSON.stringify(payload) }); },
  facilityReport(start?: string, end?: string) { if (isDemoMode()) return Promise.resolve(demoFacilityReport()); const q = new URLSearchParams(); if (start) q.set("start_date", start); if (end) q.set("end_date", end); return request<FacilityReport>(`/api/v1/reports/facility${q.toString() ? `?${q}` : ""}`); },
  listBenefitPackages() { return request<BenefitPackage[]>("/api/v1/benefits/packages"); },
  verifyShaMember(membershipNumber: string) { return request<SHAMember>(`/api/v1/admissions/sha-member?membership_number=${encodeURIComponent(membershipNumber)}`); },
  startAdmission(payload: { patient_id: string; department_id: string; benefit_package_code: string; ward: string; bed: string; diagnosis?: string | null }) { return request<Admission>("/api/v1/admissions", { method: "POST", body: JSON.stringify(payload) }); },
  requestPreauthorization(payload: { patient_id: string; coverage_id: string; payer_id: string; benefit_package_code: string; care_setting: "OUTPATIENT" | "INPATIENT"; department: string; requested_services: string[]; requested_amount: number; encounter_id?: string | null }) { return request<PreAuthorization>("/api/v1/preauthorizations", { method: "POST", body: JSON.stringify(payload) }); },
  decidePreauthorization(id: string, payload: { status: "AUTHORIZED" | "REJECTED" | "AUTHORIZED_PENDING_VISIT"; approved_amount: number; external_reference?: string | null }) { return request<PreAuthorization>(`/api/v1/preauthorizations/${id}/decision`, { method: "POST", body: JSON.stringify(payload) }); },
  listDepartments(facilityId: string) { if (isDemoMode()) return Promise.resolve(demoDepartments()); return request<Department[]>(`/api/v1/facilities/${facilityId}/departments`); },
  createEncounter(payload: EncounterCreate) { if (isDemoMode()) return Promise.resolve(demoCreateEncounter(payload)); return request<Encounter>("/api/v1/encounters", { method: "POST", body: JSON.stringify(payload) }); },
  getEncounter(id: string) { if (isDemoMode()) return Promise.resolve(demoClinicalTimeline(id).encounter); return request<Encounter>(`/api/v1/encounters/${id}`); },
  closeEncounter(id: string) { if (isDemoMode()) { const e = demoClinicalTimeline(id).encounter; e.status = "CLOSED"; e.ended_at = new Date().toISOString(); return Promise.resolve(e); } return request<Encounter>(`/api/v1/encounters/${id}/close`, { method: "POST" }); },
  getClinicalTimeline(encounterId: string) { if (isDemoMode()) return Promise.resolve(demoClinicalTimeline(encounterId)); return request<ClinicalTimeline>(`/api/v1/encounters/${encounterId}/clinical`); },
  recordVitals(encounterId: string, payload: Record<string, number | null>) { if (isDemoMode()) return Promise.resolve({ id: crypto.randomUUID(), encounter_id: encounterId, recorded_by: "demo", systolic_bp: payload.systolic_bp ?? null, diastolic_bp: payload.diastolic_bp ?? null, pulse: payload.pulse ?? null, temperature_c: payload.temperature_c ?? null, respiratory_rate: payload.respiratory_rate ?? null, oxygen_saturation: payload.oxygen_saturation ?? null, weight_kg: payload.weight_kg ?? null, height_cm: payload.height_cm ?? null, bmi: null, recorded_at: new Date().toISOString() } satisfies Vital); return request<Vital>(`/api/v1/encounters/${encounterId}/vitals`, { method: "POST", body: JSON.stringify(payload) }); },
  saveConsultation(encounterId: string, payload: Record<string, string | null>) { if (isDemoMode()) { const now = new Date().toISOString(); return Promise.resolve({ id: crypto.randomUUID(), encounter_id: encounterId, doctor_id: "demo", chief_complaint: payload.chief_complaint ?? null, history: payload.history ?? null, examination: payload.examination ?? null, assessment: payload.assessment ?? null, clinical_notes: payload.clinical_notes ?? null, treatment_plan: payload.treatment_plan ?? null, created_at: now, updated_at: now } satisfies Consultation); } return request<Consultation>(`/api/v1/encounters/${encounterId}/consultation`, { method: "POST", body: JSON.stringify(payload) }); },
  addDiagnosis(encounterId: string, payload: { diagnosis_name: string; diagnosis_code?: string | null; diagnosis_type?: string }) { if (isDemoMode()) return Promise.resolve({ id: crypto.randomUUID(), encounter_id: encounterId, diagnosis_code: payload.diagnosis_code ?? null, diagnosis_name: payload.diagnosis_name, diagnosis_type: payload.diagnosis_type || "PRIMARY", status: "ACTIVE", recorded_by: "demo", created_at: new Date().toISOString() } satisfies Diagnosis); return request<Diagnosis>(`/api/v1/encounters/${encounterId}/diagnoses`, { method: "POST", body: JSON.stringify(payload) }); },
  listAppointments() { if (isDemoMode()) return Promise.resolve(DEMO_APPOINTMENTS); return request<Appointment[]>("/api/v1/appointments"); },
  listQueues() { if (isDemoMode()) return Promise.resolve([{ id: "queue1", facility_id: "f1", department_id: "d1", name: "OPD queue", status: "ACTIVE" } satisfies Queue]); return request<Queue[]>("/api/v1/appointments/queues"); },
  listQueueEntries(queueId?: string) { if (isDemoMode()) return Promise.resolve(DEMO_QUEUE_ENTRIES); return request<QueueEntry[]>(`/api/v1/appointments/queues/entries${queueId ? `?queue_id=${queueId}` : ""}`); },
  updateQueueEntryStatus(entryId: string, newStatus: string) { if (isDemoMode()) { const entry = DEMO_QUEUE_ENTRIES.find((e) => e.id === entryId); if (!entry) return Promise.reject(new ApiError(404, "QUEUE_ENTRY_NOT_FOUND")); entry.status = newStatus; return Promise.resolve(entry); } return request<QueueEntry>(`/api/v1/appointments/queues/entries/${entryId}/${newStatus}`, { method: "PATCH" }); },
};
