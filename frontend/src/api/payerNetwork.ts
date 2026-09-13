import { getAccessToken } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export type NetworkPayer = { id: string; name: string; payer_type: string; code: string; status: string; integration_status: string };
export type NetworkPayerPlan = { id: string; payer_id: string; name: string; code: string; status: string };

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!API_BASE && import.meta.env.PROD) throw new Error("API_NOT_CONFIGURED");
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let code = "PAYER_NETWORK_REQUEST_FAILED";
    try { const body = await response.json() as { detail?: string }; if (typeof body.detail === "string") code = body.detail; } catch {}
    throw new Error(code);
  }
  return response.json() as Promise<T>;
}

export function getNetworkPayers(status?: string): Promise<NetworkPayer[]> {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return request(`/api/v1/payer-network/payers${q}`);
}

export function createNetworkPayer(payload: { name: string; payer_type: string; code: string }): Promise<NetworkPayer> {
  return request("/api/v1/payer-network/payers", { method: "POST", body: JSON.stringify(payload) });
}

export function updateNetworkPayerStatus(payerId: string, status: string, reason: string): Promise<NetworkPayer> {
  return request(`/api/v1/payer-network/payers/${payerId}/status`, { method: "PATCH", body: JSON.stringify({ status, reason }) });
}

export function getNetworkPayerPlans(payerId: string): Promise<NetworkPayerPlan[]> {
  return request(`/api/v1/payer-network/payers/${payerId}/plans`);
}

export function createNetworkPayerPlan(payerId: string, payload: { name: string; code: string }): Promise<NetworkPayerPlan> {
  return request(`/api/v1/payer-network/payers/${payerId}/plans`, { method: "POST", body: JSON.stringify(payload) });
}

export function updateNetworkPayerPlanStatus(planId: string, status: "ACTIVE" | "INACTIVE"): Promise<NetworkPayerPlan> {
  return request(`/api/v1/payer-network/plans/${planId}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
}
