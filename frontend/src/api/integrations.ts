import { getAccessToken } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export type Integration = {
  id: string;
  facility_id: string;
  name: string;
  integration_type: string;
  provider: string;
  status: string;
};

export type IntegrationTransaction = {
  id: string;
  integration_id: string;
  transaction_id: string;
  entity_type: string;
  entity_id: string | null;
  direction: string;
  request_reference: string | null;
  status: string;
  attempt_count: number;
  last_attempt_at: string | null;
  external_reference: string | null;
  response_code: string | null;
  created_at: string;
  updated_at: string;
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!API_BASE && import.meta.env.PROD) throw new Error("API_NOT_CONFIGURED");
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let code = "INTEGRATION_REQUEST_FAILED";
    try {
      const body = await response.json() as { detail?: string | { code?: string } };
      if (typeof body.detail === "string") code = body.detail;
      else if (body.detail?.code) code = body.detail.code;
    } catch {}
    throw new Error(code);
  }
  return response.json() as Promise<T>;
}

export async function getIntegrations(status?: string): Promise<Integration[]> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/v1/integrations${q}`);
}

export async function updateIntegrationStatus(integrationId: string, status: "ACTIVE" | "SUSPENDED" | "INACTIVE", reason: string): Promise<Integration> {
  return request(`/api/v1/integrations/${integrationId}/status`, { method: "PATCH", body: JSON.stringify({ status, reason }) });
}

export async function getIntegrationTransactions(filters?: { status?: string; integrationId?: string }): Promise<IntegrationTransaction[]> {
  const q = new URLSearchParams();
  if (filters?.status) q.set("status", filters.status);
  if (filters?.integrationId) q.set("integration_id", filters.integrationId);
  q.set("limit", "100");
  return request(`/api/v1/integrations/transactions?${q}`);
}
