import type { ApiErrorBody } from "./types";
import { getAccessToken, isDemoMode } from "../auth/storage";

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
  constructor(code: string) {
    super(code);
    this.code = code;
  }
}

async function coverageRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (isDemoMode()) {
    throw new CoverageApiError("DEMO_USE_LOCAL_COVERAGE");
  }
  if (!API_BASE && import.meta.env.PROD) {
    throw new CoverageApiError("API_NOT_CONFIGURED");
  }
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new CoverageApiError("API_UNREACHABLE");
  }
  if (!res.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await res.json()) as ApiErrorBody;
    } catch {
      body = null;
    }
    const code =
      typeof body?.detail === "string"
        ? body.detail
        : body?.detail && typeof body.detail === "object"
          ? body.detail.code || "REQUEST_FAILED"
          : "REQUEST_FAILED";
    throw new CoverageApiError(code || "REQUEST_FAILED");
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const DEMO_PAYERS: Payer[] = [
  { id: "pay-afya", name: "AfyaSync Membership", payer_type: "AFYASYNC", code: "AFYASYNC", status: "ACTIVE", integration_status: "INTERNAL" },
  { id: "pay-sha", name: "Social Health Authority", payer_type: "SHA", code: "SHA", status: "ACTIVE", integration_status: "NOT_CONFIGURED" },
  { id: "pay-cash", name: "Self Pay (Cash)", payer_type: "CASH", code: "CASH", status: "ACTIVE", integration_status: "INTERNAL" },
];

const DEMO_PLANS: Record<string, PayerPlan[]> = {
  "pay-afya": [{ id: "plan-afya", payer_id: "pay-afya", name: "AfyaSync Standard", code: "AFYASYNC-STANDARD", status: "ACTIVE" }],
  "pay-sha": [{ id: "plan-sha", payer_id: "pay-sha", name: "SHA / SHIF", code: "SHA-SHIF", status: "ACTIVE" }],
  "pay-cash": [{ id: "plan-cash", payer_id: "pay-cash", name: "Cash / Uninsured", code: "CASH-DEFAULT", status: "ACTIVE" }],
};

const demoCoverages: Coverage[] = [];

export const coverageApi = {
  listPayers() {
    if (isDemoMode()) return Promise.resolve(DEMO_PAYERS);
    return coverageRequest<Payer[]>("/api/v1/coverage/payers");
  },
  listPlans(payerId: string) {
    if (isDemoMode()) return Promise.resolve(DEMO_PLANS[payerId] || []);
    return coverageRequest<PayerPlan[]>(`/api/v1/coverage/payers/${payerId}/plans`);
  },
  listActiveForPatient(personId: string) {
    if (isDemoMode()) return Promise.resolve(demoCoverages.filter((c) => c.person_id === personId));
    return coverageRequest<Coverage[]>(`/api/v1/coverage/facility/person/${personId}/active`);
  },
  attach(payload: {
    person_id: string;
    payer_id: string;
    payer_plan_id?: string | null;
    membership_number?: string | null;
    start_date?: string | null;
    end_date?: string | null;
  }) {
    if (isDemoMode()) {
      const item: Coverage = {
        id: crypto.randomUUID(),
        person_id: payload.person_id,
        payer_id: payload.payer_id,
        payer_plan_id: payload.payer_plan_id ?? null,
        membership_number: payload.membership_number ?? null,
        start_date: payload.start_date ?? null,
        end_date: payload.end_date ?? null,
        verification_status: payload.payer_id === "pay-sha" ? "UNVERIFIED" : "VERIFIED",
        status: "ACTIVE",
      };
      demoCoverages.unshift(item);
      return Promise.resolve(item);
    }
    return coverageRequest<Coverage>("/api/v1/coverage", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
