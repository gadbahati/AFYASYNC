import type { NationalReport } from "./types";
import { getAccessToken } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

type NetworkFacility = {
  id: string; facility_id: string; name: string; facility_type: string;
  registration_number: string | null; license_number: string | null; county: string | null;
  sub_county: string | null; address: string | null; phone: string | null; email: string | null;
  status: string; created_at: string; updated_at: string;
};
export type NetworkFacilityInput = Omit<NetworkFacility, "id" | "facility_id" | "status" | "created_at" | "updated_at">;
export type NetworkStaff = { id: string; facility_id: string; facility_code: string; facility_name: string; person_id: string; employee_number: string; professional_number: string | null; department_id: string | null; status: string };
export type NetworkStaffList = { items: NetworkStaff[]; total: number; limit: number; offset: number };

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!API_BASE && import.meta.env.PROD) throw new Error("API_NOT_CONFIGURED");
  const token = getAccessToken(); const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) { let code = "NATIONAL_REQUEST_FAILED"; try { const body = await response.json() as { detail?: string | { code?: string } }; if (typeof body.detail === "string") code = body.detail; else if (body.detail?.code) code = body.detail.code; } catch {} throw new Error(code); }
  return response.json() as Promise<T>;
}
export async function getNationalReport(start?: string, end?: string): Promise<NationalReport> { const q = new URLSearchParams(); if (start) q.set("start_date", start); if (end) q.set("end_date", end); return request(`/api/v1/reports/national${q.toString() ? `?${q}` : ""}`); }
export async function getNetworkFacilities(filters?: { status?: string; county?: string }): Promise<NetworkFacility[]> { const q = new URLSearchParams(); if (filters?.status) q.set("facility_status", filters.status); if (filters?.county) q.set("county", filters.county); return request(`/api/v1/facilities/network${q.toString() ? `?${q}` : ""}`); }
export async function createNetworkFacility(payload: NetworkFacilityInput): Promise<NetworkFacility> { return request("/api/v1/facilities/network", { method: "POST", body: JSON.stringify(payload) }); }
export async function updateNetworkFacility(facilityId: string, payload: Partial<NetworkFacilityInput>): Promise<NetworkFacility> { return request(`/api/v1/facilities/network/${facilityId}`, { method: "PATCH", body: JSON.stringify(payload) }); }
export async function updateNetworkFacilityStatus(facilityId: string, status: "APPLICATION" | "ACTIVE" | "SUSPENDED" | "INACTIVE", reason: string): Promise<NetworkFacility> { return request(`/api/v1/facilities/network/${facilityId}/status`, { method: "PATCH", body: JSON.stringify({ status, reason }) }); }
export async function getNetworkStaff(filters?: { facilityId?: string; status?: string }): Promise<NetworkStaffList> { const q = new URLSearchParams(); if (filters?.facilityId) q.set("facility_id", filters.facilityId); if (filters?.status) q.set("status", filters.status); return request(`/api/v1/staff/network?${q}`); }
