import type { ApiErrorBody } from "./types";
import { getAccessToken } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export type Payer = {
  id: string;
  name: string;
  payer_type: string;
  code: string;
  status: string;
  integration_status: string;
};

export type PayerPlan = {
  id: string;
  payer_id: string;
  name: string;
  code: string;
  status: string;
};

export type Coverage = {
  id: string;
  person_id: string;
  payer_id: string;
  payer_plan_id: string | null;
  membership_number: string | null;
  start_date: string | null;
  end_date: string | null;
  verification_status: string;
  status: string;
};

class CoverageApiError extends Error {
  code: string;
  constructor(code: string) { super(code); this.code = code; }
}

async function coverageRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!API_BASE && import.meta.env.PROD) throw new CoverageApiError("API_NOT_CONFIGURED");
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res: Response;
  try { res = await fetch(`${API_BASE}${path}`, { ...init, headers }); }
  catch { throw new CoverageApiError("API_UNREACHABLE"); }
  if (!res.ok) {
    let body: ApiErrorBody | null = null;
    try { body = await res.json() as ApiErrorBody; } catch { body = null; }
    const code = typeof body?.detail === "string" ? body.detail : body?.detail && typeof body.detail === "object" ? body.detail.code || "REQUEST_FAILED" : "REQUEST_FAILED";
    throw new CoverageApiError(code || "REQUEST_FAILED");
  }
  if (res.status === 204) return undefined as T;
  return await res.json() as T;
}

export const coverageApi = {
  listPayers() { return coverageRequest<Payer[]>("/api/v1/coverage/payers"); },
  listPlans(payerId: string) { return coverageRequest<PayerPlan[]>(`/api/v1/coverage/payers/${payerId}/plans`); },
  listActiveForPatient(personId: string) { return coverageRequest<Coverage[]>(`/api/v1/coverage/facility/person/${personId}/active`); },
  attach(payload: { person_id: string; payer_id: string; payer_plan_id?: string | null; membership_number?: string | null; start_date?: string | null; end_date?: string | null; }) {
    return coverageRequest<Coverage>("/api/v1/coverage", { method: "POST", body: JSON.stringify(payload) });
  },
};
