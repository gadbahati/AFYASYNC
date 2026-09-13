import { getAccessToken } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export type NetworkBenefitRule = {
  id: string;
  payer_id: string;
  payer_plan_id: string | null;
  service_code: string | null;
  service_type: string | null;
  payer_percent: number;
  fixed_patient_copay: number;
  max_covered_amount: number | null;
  effective_from: string | null;
  effective_to: string | null;
  status: string;
};

export type NetworkBenefitRuleInput = Omit<NetworkBenefitRule, "id" | "status">;

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!API_BASE && import.meta.env.PROD) throw new Error("API_NOT_CONFIGURED");
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    let code = "BENEFIT_NETWORK_REQUEST_FAILED";
    try {
      const body = await response.json() as { detail?: string | { code?: string } };
      if (typeof body.detail === "string") code = body.detail;
      else if (body.detail?.code) code = body.detail.code;
    } catch {}
    throw new Error(code);
  }
  return response.json() as Promise<T>;
}

export async function getNetworkBenefitRules(filters?: { payerId?: string; payerPlanId?: string; status?: string }): Promise<NetworkBenefitRule[]> {
  const q = new URLSearchParams();
  if (filters?.payerId) q.set("payer_id", filters.payerId);
  if (filters?.payerPlanId) q.set("payer_plan_id", filters.payerPlanId);
  if (filters?.status) q.set("rule_status", filters.status);
  return request(`/api/v1/payer-network/benefits/rules${q.toString() ? `?${q}` : ""}`);
}

export async function createNetworkBenefitRule(payload: NetworkBenefitRuleInput): Promise<NetworkBenefitRule> {
  return request("/api/v1/payer-network/benefits/rules", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateNetworkBenefitRuleStatus(ruleId: string, status: "ACTIVE" | "INACTIVE", reason: string): Promise<NetworkBenefitRule> {
  return request(`/api/v1/payer-network/benefits/rules/${ruleId}/status`, { method: "PATCH", body: JSON.stringify({ status, reason }) });
}
