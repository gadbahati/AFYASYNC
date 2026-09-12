import type {
  ApiErrorBody,
  AuthMe,
  ClinicalTimeline,
  Consultation,
  Department,
  Diagnosis,
  Encounter,
  EncounterCreate,
  FacilityOption,
  FacilityReport,
  LoginResult,
  Patient,
  PatientCreate,
  PatientListResponse,
  TokenResponse,
  Vital,
} from "./types";
import { clearSession, getAccessToken, getRefreshToken, setSession } from "../auth/storage";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message?: string) {
    super(message || code);
    this.status = status;
    this.code = code;
  }
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
  const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    clearSession();
    return false;
  }
  const data = (await res.json()) as TokenResponse;
  setSession({ access_token: data.access_token, refresh_token: data.refresh_token });
  return true;
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (res.status === 401 && retry) {
    if (!refreshPromise) refreshPromise = tryRefresh().finally(() => { refreshPromise = null; });
    const ok = await refreshPromise;
    if (ok) return request<T>(path, init, false);
  }

  if (!res.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await res.json()) as ApiErrorBody;
    } catch {
      body = null;
    }
    throw new ApiError(res.status, parseDetail(body));
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login(username: string, password: string) {
    return request<LoginResult>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }, false);
  },
  selectFacility(facility_id: string) {
    return request<TokenResponse>("/api/v1/auth/select-facility", {
      method: "POST",
      body: JSON.stringify({ facility_id }),
    }, false);
  },
  facilities() {
    return request<FacilityOption[]>("/api/v1/auth/facilities");
  },
  me() {
    return request<AuthMe>("/api/v1/auth/me");
  },
  logout(refresh_token: string) {
    return request<{ success: boolean }>("/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }, false);
  },
  listPatients(limit = 50, offset = 0) {
    return request<PatientListResponse>(`/api/v1/patients?limit=${limit}&offset=${offset}`);
  },
  getPatient(id: string) {
    return request<Patient>(`/api/v1/patients/${id}`);
  },
  createPatient(payload: PatientCreate) {
    return request<Patient>("/api/v1/patients", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  facilityReport(start?: string, end?: string) {
    const q = new URLSearchParams();
    if (start) q.set("start_date", start);
    if (end) q.set("end_date", end);
    const suffix = q.toString() ? `?${q}` : "";
    return request<FacilityReport>(`/api/v1/reports/facility${suffix}`);
  },
  listDepartments(facilityId: string) {
    return request<Department[]>(`/api/v1/facilities/${facilityId}/departments`);
  },
  createEncounter(payload: EncounterCreate) {
    return request<Encounter>("/api/v1/encounters", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getEncounter(id: string) {
    return request<Encounter>(`/api/v1/encounters/${id}`);
  },
  closeEncounter(id: string) {
    return request<Encounter>(`/api/v1/encounters/${id}/close`, { method: "POST" });
  },
  getClinicalTimeline(encounterId: string) {
    return request<ClinicalTimeline>(`/api/v1/encounters/${encounterId}/clinical`);
  },
  recordVitals(encounterId: string, payload: Record<string, number | null>) {
    return request<Vital>(`/api/v1/encounters/${encounterId}/vitals`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  saveConsultation(encounterId: string, payload: Record<string, string | null>) {
    return request<Consultation>(`/api/v1/encounters/${encounterId}/consultation`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  addDiagnosis(encounterId: string, payload: { diagnosis_name: string; diagnosis_code?: string | null; diagnosis_type?: string }) {
    return request<Diagnosis>(`/api/v1/encounters/${encounterId}/diagnoses`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
