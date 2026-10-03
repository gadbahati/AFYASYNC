import { clearSession, getAccessToken, getAccountType, getRefreshToken, setSession } from "../auth/storage";
import type { ApiErrorBody, TokenResponse } from "./types";
import { citizenApiMethods } from "./citizenApi";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const AUTH_EXPIRED_EVENT = "afyasync:auth-expired";

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message?: string) {
    super(message || code);
    this.status = status;
    this.code = code;
  }
}

function parseError(body: ApiErrorBody | null, status: number): { code: string; message?: string } {
  if (!body) return { code: status >= 500 ? "SERVER_ERROR" : "REQUEST_FAILED" };
  if (typeof body.detail === "string") return { code: body.detail };
  if (body.detail) return { code: body.detail.code || "REQUEST_FAILED", message: body.detail.message };
  const message = typeof body.message === "string" ? body.message : undefined;
  const requestId =
    body.data && typeof body.data === "object" && typeof body.data.request_id === "string"
      ? body.data.request_id
      : undefined;
  if (status >= 500) return { code: requestId ? `SERVER_ERROR:${requestId}` : "SERVER_ERROR", message };
  return { code: message || "REQUEST_FAILED", message };
}

function notifyAuthExpired(): void {
  clearSession();
  if (typeof window !== "undefined") window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
}

let refreshPromise: Promise<boolean> | null = null;
async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) {
      notifyAuthExpired();
      return false;
    }
    const data = (await res.json()) as TokenResponse;
    setSession({
      access_token: data.access_token,
      refresh_token: data.refresh_token,
      account_type: getAccountType(),
    });
    return true;
  } catch {
    notifyAuthExpired();
    return false;
  }
}

async function request<T = any>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  if (!API_BASE && import.meta.env.PROD) throw new ApiError(0, "API_NOT_CONFIGURED");
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "API_UNREACHABLE");
  }
  if (res.status === 401 && retry) {
    if (!refreshPromise)
      refreshPromise = tryRefresh().finally(() => {
        refreshPromise = null;
      });
    if (await refreshPromise) return request<T>(path, init, false);
  }
  if (!res.ok) {
    let body: ApiErrorBody | null = null;
    try {
      body = (await res.json()) as ApiErrorBody;
    } catch {}
    const parsed = parseError(body, res.status);
    if (
      res.status === 401 &&
      !path.includes("/auth/login") &&
      !path.includes("/auth/patient") &&
      !path.includes("/auth/refresh") &&
      !path.includes("/auth/logout")
    ) {
      notifyAuthExpired();
    }
    throw new ApiError(res.status, parsed.code, parsed.message);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const _apiCore: any = {
  contextOverview: (scope?: string) =>
    request("/api/v1/context" + (scope ? `?scope=${encodeURIComponent(scope)}` : "")),
  contextScopeSummary: (scope: string = "facility") =>
    request(`/api/v1/context/scope-summary?scope=${encodeURIComponent(scope)}`),
  contextOperationsSummary: (scope: string = "facility", start?: string, end?: string) => {
    const q = new URLSearchParams({ scope });
    if (start) q.set("start_date", start);
    if (end) q.set("end_date", end);
    return request(`/api/v1/context/operations-summary?${q.toString()}`);
  },
  setOperatingScope: (scope: string, previous_scope?: string) => {
    const q = new URLSearchParams({ scope });
    if (previous_scope) q.set("previous_scope", previous_scope);
    return request(`/api/v1/context/scope?${q.toString()}`, { method: "POST" });
  },
  login: (username: string, password: string) =>
    request("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }, false),
  patientLogin: (identifier: string, password: string) =>
    request("/api/v1/auth/patient/login", { method: "POST", body: JSON.stringify({ identifier, password }) }, false),
  patientRegister: (payload: {
    afya_id: string;
    password: string;
    first_name?: string;
    last_name?: string;
    phone?: string;
    email?: string;
  }) => request("/api/v1/auth/patient/register", { method: "POST", body: JSON.stringify(payload) }, false),
  patientPasswordResetRequest: (identifier: string, channel: "PHONE" | "EMAIL") =>
    request("/api/v1/auth/patient/password-reset/request", { method: "POST", body: JSON.stringify({ identifier, channel }) }, false),
  patientPasswordResetConfirm: (identifier: string, code: string, new_password: string) =>
    request("/api/v1/auth/patient/password-reset/confirm", { method: "POST", body: JSON.stringify({ identifier, code, new_password }) }, false),
  selectFacility: (facility_id: string) =>
    request("/api/v1/auth/select-facility", { method: "POST", body: JSON.stringify({ facility_id }) }, false),
  facilities: () => request("/api/v1/auth/facilities"),
  facilityDirectory: (search = "", page = 1, pageSize = 30) =>
    request(
      `/api/v1/facilities/directory?search=${encodeURIComponent(search.trim())}&page=${page}&page_size=${pageSize}`,
    ),
  facilityReport: (start?: string, end?: string) =>
    request(
      `/api/v1/reports/facility${start || end ? `?start_date=${start || ""}&end_date=${end || ""}` : ""}`,
    ),
  listReferrals: (role = "all", scope = "facility") =>
    request(`/api/v1/referrals?role=${encodeURIComponent(role)}&scope=${encodeURIComponent(scope)}`),
  listTransfers: (role = "all", scope = "facility") =>
    request(`/api/v1/referrals/transfers?role=${encodeURIComponent(role)}&scope=${encodeURIComponent(scope)}`),
  listAppointments: (scope = "facility", appointment_date?: string) => {
    const q = new URLSearchParams({ scope });
    if (appointment_date) q.set("appointment_date", appointment_date);
    return request(`/api/v1/appointments?${q.toString()}`);
  },
  listBillingServices: (scope = "facility") =>
    request(`/api/v1/billing/services?scope=${encodeURIComponent(scope)}`),
  listInvoices: (limit = 50, scope = "facility") =>
    request(`/api/v1/billing/invoices?limit=${limit}&scope=${encodeURIComponent(scope)}`),
  listPatients: (limit = 50, offset = 0, scope = "facility") =>
    request(`/api/v1/patients?limit=${limit}&offset=${offset}&scope=${encodeURIComponent(scope)}`),
  searchPatients: (q: string, limit = 20, scope = "facility") =>
    request(`/api/v1/patients/search?q=${encodeURIComponent(q)}&limit=${limit}&scope=${encodeURIComponent(scope)}`),
  listEncounters: (limit = 100, offset = 0, scope = "facility") =>
    request(`/api/v1/encounters?limit=${limit}&offset=${offset}&scope=${encodeURIComponent(scope)}`),
  listClaims: (limit = 50, scope = "facility") =>
    request(`/api/v1/claims?limit=${limit}&scope=${encodeURIComponent(scope)}`),
  getPatient: (id: string) => request(`/api/v1/patients/${id}`),
  createPatient: (payload: any) => request("/api/v1/patients", { method: "POST", body: JSON.stringify(payload) }),
  benefitQuote: (payload: any) =>
    request("/api/v1/benefit-engine/quote", { method: "POST", body: JSON.stringify(payload) }),
  benefitQuoteBatch: (payload: any) =>
    request("/api/v1/benefit-engine/quote-batch", { method: "POST", body: JSON.stringify(payload) }),
  benefitRules: (params: { payer_id?: string; payer_plan_id?: string; status?: string } = {}) => {
    const q = new URLSearchParams();
    if (params.payer_id) q.set("payer_id", params.payer_id);
    if (params.payer_plan_id) q.set("payer_plan_id", params.payer_plan_id);
    if (params.status) q.set("status", params.status);
    const qs = q.toString();
    return request(`/api/v1/benefit-engine/rules${qs ? `?${qs}` : ""}`);
  },
  createBenefitRule: (payload: any) =>
    request("/api/v1/benefit-engine/rules", { method: "POST", body: JSON.stringify(payload) }),
  importBenefitRules: (payload: { rules: any[]; stop_on_error?: boolean }) =>
    request("/api/v1/benefit-engine/rules/import", { method: "POST", body: JSON.stringify(payload) }),
  listBenefitPackages: () => request("/api/v1/benefits/packages"),
  repriceInvoiceBenefits: (invoiceId: string) =>
    request(`/api/v1/billing/invoices/${invoiceId}/reprice-benefits`, { method: "POST" }),
  settlementCreateObligation: (claimId: string) =>
    request("/api/v1/settlements/obligations", { method: "POST", body: JSON.stringify({ claim_id: claimId }) }),
  settlementCreateBatch: (payerId: string) =>
    request("/api/v1/settlements/batches", { method: "POST", body: JSON.stringify({ payer_id: payerId }) }),
  settlementRecordPayment: (
    batchId: string,
    payload: { obligation_id: string; amount: number; method?: string },
  ) =>
    request(`/api/v1/settlements/batches/${batchId}/payments`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  settlementReconcile: (payload: { batch_id: string; received_amount: number }) =>
    request(`/api/v1/settlements/batches/${payload.batch_id}/reconcile`, {
      method: "POST",
      body: JSON.stringify({ received_amount: payload.received_amount }),
    }),
  settlementListBatches: () => request("/api/v1/settlements/batches"),
  settlementOverview: () => request("/api/v1/settlements/overview"),
  claimPreflight: (invoiceId: string) => request(`/api/v1/claims/invoices/${invoiceId}/preflight`),
  adjudicateClaim: (claimId: string, force = false) =>
    request("/api/v1/adjudication/run", {
      method: "POST",
      body: JSON.stringify({ claim_id: claimId, force }),
    }),
  getClaimAdjudication: (claimId: string) => request(`/api/v1/adjudication/claims/${claimId}`),
  getClaimAdjudicationLines: (claimId: string) =>
    request(`/api/v1/adjudication/claims/${claimId}/lines`),
  createClaim: (invoiceId: string) =>
    request("/api/v1/claims", { method: "POST", body: JSON.stringify({ invoice_id: invoiceId }) }),
  validateClaim: (claimId: string) =>
    request(`/api/v1/claims/${claimId}/validate`, { method: "POST" }),
  submitClaim: (claimId: string) =>
    request(`/api/v1/claims/${claimId}/submit`, { method: "POST" }),
  recordClaimResponse: (claimId: string, payload: any) =>
    request(`/api/v1/claims/${claimId}/response`, { method: "POST", body: JSON.stringify(payload) }),
  reconcileClaim: (claimId: string, received_amount: number) =>
    request(`/api/v1/claims/${claimId}/reconcile`, {
      method: "POST",
      body: JSON.stringify({ received_amount }),
    }),
  listClaimRejections: () => request("/api/v1/claims/workbench/rejections"),
  claimsKesAtRisk: (days = 7) => request(`/api/v1/claims/risk/kes-at-risk?days=${days}`),
  sandboxRejectClaim: (claimId: string, payload: object = {}) =>
    request(`/api/v1/claims/${claimId}/sandbox-reject`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  financingPreauthCreate: (payload: any) =>
    request("/api/v1/financing-preauthorizations", { method: "POST", body: JSON.stringify(payload) }),
  financingPreauthDecide: (id: string, payload: any) =>
    request(`/api/v1/financing-preauthorizations/${id}/decision`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  financingPreauthList: (params: { status?: string; person_id?: string; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.status) q.set("status", params.status);
    if (params.person_id) q.set("person_id", params.person_id);
    if (params.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request(`/api/v1/financing-preauthorizations${qs ? `?${qs}` : ""}`);
  },
  me: () => request("/api/v1/auth/me"),
  logout: (refresh_token?: string) =>
    request("/api/v1/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token }) }, false),
};

export const api: any = { ..._apiCore, ...citizenApiMethods(request) };

export { request, API_BASE, AUTH_EXPIRED_EVENT };
