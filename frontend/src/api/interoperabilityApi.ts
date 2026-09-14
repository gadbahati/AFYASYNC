import { getAccessToken, refreshAccessToken } from "../auth/storage";

export type FHIRPatientResource = {
  resourceType: "Patient";
  id: string;
  identifier: Array<{ system: string; value: string }>;
  name: Array<{ use: string; family: string; given: string[] }>;
  birthDate: string | null;
  gender: string | null;
  active: boolean;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
if (!API_BASE && import.meta.env.PROD) throw new Error("VITE_API_BASE_URL is required in production");

async function request(path: string, retry = true): Promise<Response> {
  const token = getAccessToken();
  if (!token) throw new Error("AUTH_REQUIRED");
  const response = await fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (response.status === 401 && retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return request(path, false);
  }
  return response;
}

export async function getFHIRPatient(patientId: string): Promise<FHIRPatientResource> {
  const response = await request(`/api/v1/interoperability/Patient/${encodeURIComponent(patientId)}`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "INTEROPERABILITY_READ_FAILED");
  return body as FHIRPatientResource;
}
