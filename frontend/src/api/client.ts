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
  contextOverview: (scope?: string, tenantId?: string | null) => {
    const q = new URLSearchParams();
    if (scope) q.set("scope", scope);
    if (tenantId) q.set("tenant_id", tenantId);
    const qs = q.toString();
    return request("/api/v1/context" + (qs ? `?${qs}` : ""));
  },
  contextScopeSummary: (scope: string = "facility", tenantId?: string | null) => {
    const q = new URLSearchParams({ scope });
    if (tenantId) q.set("tenant_id", tenantId);
    return request(`/api/v1/context/scope-summary?${q.toString()}`);
  },
  contextOperationsSummary: (scope: string = "facility", start?: string, end?: string, tenantId?: string | null) => {
    const q = new URLSearchParams({ scope });
    if (tenantId) q.set("tenant_id", tenantId);
    if (start) q.set("start_date", start);
    if (end) q.set("end_date", end);
    return request(`/api/v1/context/operations-summary?${q.toString()}`);
  },
  tenancyOverview: () => request("/api/v1/tenancy"),
  tenancyCreateOrganization: (payload: any) =>
    request("/api/v1/tenancy/organizations", { method: "POST", body: JSON.stringify(payload) }),
  tenancyAttachFacility: (organizationId: string, facilityId: string) =>
    request(`/api/v1/tenancy/organizations/${organizationId}/facilities/${facilityId}`, { method: "POST" }),
  tenancyAttachUser: (organizationId: string, userId: string, accessLevel = "MEMBER") =>
    request(`/api/v1/tenancy/organizations/${organizationId}/users/${userId}?access_level=${encodeURIComponent(accessLevel)}`, { method: "POST" }),
  tenancyGrantGovernmentAccess: (organizationId: string, userId: string, roleCode = "HEALTH_OFFICER", scopeLevel = "COUNTY") =>
    request("/api/v1/tenancy/organizations/" + organizationId + "/government-access/" + userId + "?role_code=" + encodeURIComponent(roleCode) + "&scope_level=" + encodeURIComponent(scopeLevel), { method: "POST" }),
  tenancySelect: (organizationId: string) =>
    request(`/api/v1/tenancy/select?organization_id=${encodeURIComponent(organizationId)}`, { method: "POST" }),
  downloadWarehouseCsv: async (days = 30) => {
    const token = getAccessToken();
    const headers = new Headers();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const res = await fetch(`${API_BASE}/api/v1/warehouse/export/county-facts.csv?days=${days}`, { headers });
    if (!res.ok) throw new ApiError(res.status, "WAREHOUSE_EXPORT_FAILED");
    return res.text();
  },
  businessContinuityOverview: () => request("/api/v1/business-continuity"),
  businessContinuityCreatePlan: (payload: any) =>
    request("/api/v1/business-continuity/plans", { method: "POST", body: JSON.stringify(payload) }),
  productReadiness: () => request("/api/v1/product-readiness"),
  runEndToEndSimulation: () => request("/api/v1/end-to-end-simulation/run", { method: "POST" }),
  businessContinuityRecordTest: (planId: string, payload: any) =>
    request(`/api/v1/business-continuity/plans/${planId}/tests`, { method: "POST", body: JSON.stringify(payload) }),
  setOperatingScope: (scope: string, previous_scope?: string, tenant_id?: string | null) => {
    const q = new URLSearchParams({ scope });
    if (previous_scope) q.set("previous_scope", previous_scope);
    if (tenant_id) q.set("tenant_id", tenant_id);
    return request(`/api/v1/context/scope?${q.toString()}`, { method: "POST" });
  },
  login: (username: string, password: string) =>
    request("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }, false),
  governmentLogin: (username: string, password: string) =>
    request("/api/v1/auth/government/login", { method: "POST", body: JSON.stringify({ username, password }) }, false),
  governmentOrganizations: () => request("/api/v1/auth/government/organizations"),
  selectGovernmentOrganization: (organizationId: string) =>
    request("/api/v1/auth/government/select-organization?organization_id=" + encodeURIComponent(organizationId), { method: "POST" }),
  governmentMe: () => request("/api/v1/auth/government/me"),
  governmentMFASetup: () => request("/api/v1/auth/government/mfa/setup", { method: "POST" }),
  governmentMFAConfirmSetup: (code: string) => request("/api/v1/auth/government/mfa/confirm-setup", { method: "POST", body: JSON.stringify({ code }) }, false),
  governmentMFAVerify: (challengeId: string, code: string) => request(`/api/v1/auth/government/mfa/verify?challenge_id=${encodeURIComponent(challengeId)}&code=${encodeURIComponent(code)}`, { method: "POST" }, false),
  governmentOverview: () => request("/api/v1/government/overview"),
  portalResults: (limit = 50) => request(`/api/v1/portal/results?limit=${limit}`),
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
  getClinicalTimeline: (encounterId: string) => request(`/api/v1/encounters/${encounterId}/clinical`),
  recordVitals: (encounterId: string, payload: any) => request(`/api/v1/encounters/${encounterId}/vitals`, { method: "POST", body: JSON.stringify(payload) }),
  saveConsultation: (encounterId: string, payload: any) => request(`/api/v1/encounters/${encounterId}/consultation`, { method: "POST", body: JSON.stringify(payload) }),
  addDiagnosis: (encounterId: string, payload: any) => request(`/api/v1/encounters/${encounterId}/diagnoses`, { method: "POST", body: JSON.stringify(payload) }),
  getProcedures: (encounterId: string) => request(`/api/v1/encounters/${encounterId}/procedures`),
  addProcedure: (encounterId: string, payload: any) => request(`/api/v1/encounters/${encounterId}/procedures`, { method: "POST", body: JSON.stringify(payload) }),
  getClinicalNotes: (encounterId: string) => request(`/api/v1/encounters/${encounterId}/clinical-notes`),
  addClinicalNote: (encounterId: string, payload: any) => request(`/api/v1/encounters/${encounterId}/clinical-notes`, { method: "POST", body: JSON.stringify(payload) }),
  listClinicalOrders: (encounterId: string, orderType?: string) => {
    const q = orderType ? `?order_type=${encodeURIComponent(orderType)}` : "";
    return request(`/api/v1/encounters/${encounterId}/orders${q}`);
  },
  createClinicalOrder: (encounterId: string, payload: any) =>
    request(`/api/v1/encounters/${encounterId}/orders`, { method: "POST", body: JSON.stringify(payload) }),
  fulfillClinicalOrder: (orderId: string, payload: { status?: string; result_notes?: string } = {}) =>
    request(`/api/v1/encounters/orders/${orderId}/fulfill`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  forwardClinicalOrder: (orderId: string) =>
    request(`/api/v1/encounters/orders/${orderId}/forward`, { method: "POST" }),
  updateClinicalOrderStatus: (orderId: string, status: string) =>
    request(`/api/v1/encounters/orders/${orderId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  dischargeEncounter: (encounterId: string, payload: any) =>
    request(`/api/v1/encounters/${encounterId}/discharge`, { method: "POST", body: JSON.stringify(payload) }),
  getEncounterDischarge: (encounterId: string) =>
    request(`/api/v1/encounters/${encounterId}/discharge`),
  getLatestTriage: (encounterId: string) => request(`/api/v1/encounters/${encounterId}/triage`),
  recordTriage: (encounterId: string, payload: any) => request(`/api/v1/encounters/${encounterId}/triage`, { method: "POST", body: JSON.stringify(payload) }),
  updateAppointmentStatus: (appointmentId: string, status: string) => request(`/api/v1/appointments/${appointmentId}/${encodeURIComponent(status)}`, { method: "PATCH" }),
  listDepartments: () => request("/api/v1/facilities/me/departments"),
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
  mpiCandidates: (params: { first_name?: string; last_name?: string; date_of_birth?: string; phone?: string; national_id_number?: string }) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => { if (value) query.set(key, value); });
    return request("/api/v1/patients/mpi/candidates?" + query.toString());
  },
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
  settlementListObligations: (params: { claim_id?: string; status?: string; limit?: number } = {}) => {
    const q = new URLSearchParams();
    if (params.claim_id) q.set("claim_id", params.claim_id);
    if (params.status) q.set("status", params.status);
    if (params.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request(`/api/v1/settlements/obligations${qs ? `?${qs}` : ""}`);
  },
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
  fraudScanClaim: (claimId: string) =>
    request(`/api/v1/claims/${claimId}/fraud-scan`, { method: "POST" }),
  appealClaim: (claimId: string, payload: { reason: string; evidence_ref?: string }) =>
    request(`/api/v1/claims/${claimId}/appeal`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
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

export async function downloadWarehouseCsv(days = 30): Promise<string> {
  const token = getAccessToken();
  const headers = new Headers();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_BASE}/api/v1/warehouse/export/county-facts.csv?days=${days}`, { headers });
  if (!res.ok) throw new ApiError(res.status, "WAREHOUSE_EXPORT_FAILED");
  return res.text();
}
