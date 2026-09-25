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
  const requestId = body.data && typeof body.data === "object" && typeof body.data.request_id === "string" ? body.data.request_id : undefined;
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
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: refresh }) });
    if (!res.ok) { notifyAuthExpired(); return false; }
    const data = (await res.json()) as TokenResponse;
    setSession({ access_token: data.access_token, refresh_token: data.refresh_token, account_type: getAccountType() });
    return true;
  } catch { notifyAuthExpired(); return false; }
}

async function request<T = any>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  if (!API_BASE && import.meta.env.PROD) throw new ApiError(0, "API_NOT_CONFIGURED");
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let res: Response;
  try { res = await fetch(`${API_BASE}${path}`, { ...init, headers }); }
  catch { throw new ApiError(0, "API_UNREACHABLE"); }
  if (res.status === 401 && retry) {
    if (!refreshPromise) refreshPromise = tryRefresh().finally(() => { refreshPromise = null; });
    if (await refreshPromise) return request<T>(path, init, false);
  }
  if (!res.ok) {
    let body: ApiErrorBody | null = null;
    try { body = (await res.json()) as ApiErrorBody; } catch {}
    const parsed = parseError(body, res.status);
    if (res.status === 401 && !path.includes("/auth/login") && !path.includes("/auth/patient") && !path.includes("/auth/refresh") && !path.includes("/auth/logout")) notifyAuthExpired();
    throw new ApiError(res.status, parsed.code, parsed.message);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const _apiCore: any = {
  login: (username: string, password: string) => request("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }, false),
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
  selectFacility: (facility_id: string) => request("/api/v1/auth/select-facility", { method: "POST", body: JSON.stringify({ facility_id }) }, false),
  facilities: () => request("/api/v1/auth/facilities"),
  facilityDirectory: (search = "", page = 1, pageSize = 30) => request(`/api/v1/facilities/directory?search=${encodeURIComponent(search.trim())}&page=${page}&page_size=${pageSize}`),
  addDirectoryFacility: (payload: any) => request("/api/v1/facilities/directory", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request("/api/v1/auth/me"),
  logout: (refresh_token: string) => request("/api/v1/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token }) }, false),

  portalMe: () => request("/api/v1/portal/me"),
  portalEncounters: (limit = 50, offset = 0) => request(`/api/v1/portal/encounters?limit=${limit}&offset=${offset}`),
  portalEncounterSummary: (id: string) => request(`/api/v1/portal/encounters/${id}`),
  portalConsents: () => request("/api/v1/portal/consents"),
  portalUpdateConsent: (id: string, payload: any) => request(`/api/v1/portal/consents/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  portalCoverage: () => request("/api/v1/portal/coverage"),
  portalFacilities: () => request("/api/v1/portal/facilities"),
  portalBookAppointment: (payload: any) => request("/api/v1/portal/appointment-requests", { method: "POST", body: JSON.stringify(payload) }),
  portalAppointmentRequests: () => request("/api/v1/portal/appointment-requests"),
  portalCancelAppointmentRequest: (id: string) => request(`/api/v1/portal/appointment-requests/${id}/cancel`, { method: "POST" }),
  portalMessageThreads: () => request("/api/v1/portal/messages/threads"),
  portalMessageThread: (facilityId: string) => request(`/api/v1/portal/messages/${facilityId}`),
  portalMessageTemplates: () => request("/api/v1/portal/messages/templates"),
  portalSendMessage: (payload: any) => request("/api/v1/portal/messages", { method: "POST", body: JSON.stringify(payload) }),
  facilityAppointmentRequests: (status?: string) => request(`/api/v1/facility/appointment-requests${status ? `?status=${status}` : ""}`),
  facilityRespondAppointment: (id: string, payload: any) => request(`/api/v1/facility/appointment-requests/${id}/respond`, { method: "POST", body: JSON.stringify(payload) }),
  facilityMessageInbox: () => request("/api/v1/facility/messages/inbox"),
  facilityMessageThread: (patientId: string) => request(`/api/v1/facility/messages/${patientId}`),
  facilityMessageTemplates: () => request("/api/v1/facility/messages/templates"),
  facilitySendMessage: (payload: any) => request("/api/v1/facility/messages", { method: "POST", body: JSON.stringify(payload) }),

  listTreatAbroadProcedures: () => request("/api/v1/treat-abroad/procedures"),
  listTreatAbroadCases: (status?: string) => request(`/api/v1/treat-abroad/cases${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  createTreatAbroadCase: (payload: any) => request("/api/v1/treat-abroad/cases", { method: "POST", body: JSON.stringify(payload) }),
  updateTreatAbroadCase: (id: string, payload: any) => request(`/api/v1/treat-abroad/cases/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),

  listPatients: (limit = 50, offset = 0) => request(`/api/v1/patients?limit=${limit}&offset=${offset}`),
  getPatient: (id: string) => request(`/api/v1/patients/${id}`),
  getPatientRecord: (id: string) => request(`/api/v1/patients/${id}/summary`),
  getPatientTimeline: (id: string, limit = 50, offset = 0) => request(`/api/v1/patients/${id}/timeline?limit=${limit}&offset=${offset}`),
  createPatient: (payload: any) => request("/api/v1/patients", { method: "POST", body: JSON.stringify(payload) }),
  listPatientAllergies: (id: string, includeInactive = false) => request(`/api/v1/patients/${id}/allergies?include_inactive=${includeInactive}`),
  createPatientAllergy: (id: string, payload: any) => request(`/api/v1/patients/${id}/allergies`, { method: "POST", body: JSON.stringify(payload) }),
  updatePatientAllergy: (id: string, allergyId: string, payload: any) => request(`/api/v1/patients/${id}/allergies/${allergyId}`, { method: "PATCH", body: JSON.stringify(payload) }),

  facilityReport: (start?: string, end?: string) => request(`/api/v1/reports/facility${start || end ? `?start_date=${start || ""}&end_date=${end || ""}` : ""}`),
  facilityOperationsReport: (start?: string, end?: string) => request(`/api/v1/reports/facility/operations${start || end ? `?start_date=${start || ""}&end_date=${end || ""}` : ""}`),
  listBenefitPackages: () => request("/api/v1/benefits/packages"),
  verifyShaMember: (membershipNumber: string) => request(`/api/v1/admissions/sha-member?membership_number=${encodeURIComponent(membershipNumber)}`),
  startAdmission: (payload: any) => request("/api/v1/admissions", { method: "POST", body: JSON.stringify(payload) }),
  requestPreauthorization: (payload: any) => request("/api/v1/preauthorizations", { method: "POST", body: JSON.stringify(payload) }),
  decidePreauthorization: (id: string, payload: any) => request(`/api/v1/preauthorizations/${id}/decision`, { method: "POST", body: JSON.stringify(payload) }),

  listDepartments: (facilityId: string) => request(`/api/v1/facilities/${facilityId}/departments`),
  createEncounter: (payload: any) => request("/api/v1/encounters", { method: "POST", body: JSON.stringify(payload) }),
  getEncounter: (id: string) => request(`/api/v1/encounters/${id}`),
  closeEncounter: (id: string) => request(`/api/v1/encounters/${id}/close`, { method: "POST" }),
  getClinicalTimeline: (encounterId: string) => request(`/api/v1/encounters/${encounterId}/clinical`),
  recordVitals: (encounterId: string, payload: any) => request(`/api/v1/encounters/${encounterId}/vitals`, { method: "POST", body: JSON.stringify(payload) }),
  saveConsultation: (encounterId: string, payload: any) => request(`/api/v1/encounters/${encounterId}/consultation`, { method: "POST", body: JSON.stringify(payload) }),
  addDiagnosis: (encounterId: string, payload: any) => request(`/api/v1/encounters/${encounterId}/diagnoses`, { method: "POST", body: JSON.stringify(payload) }),

  listAppointments: () => request("/api/v1/appointments"),
  createAppointment: (payload: any) => request("/api/v1/appointments", { method: "POST", body: JSON.stringify(payload) }),
  listReferrals: (role = "all") => request(`/api/v1/referrals?role=${role}`),
  createReferral: (payload: any) => request("/api/v1/referrals", { method: "POST", body: JSON.stringify(payload) }),
  updateReferralStatus: (id: string, status: string) => request(`/api/v1/referrals/${id}/status`, { method: "POST", body: JSON.stringify({ status }) }),
  listTransfers: (role = "all") => request(`/api/v1/referrals/transfers?role=${role}`),
  createTransfer: (payload: any) => request("/api/v1/referrals/transfers", { method: "POST", body: JSON.stringify(payload) }),
  updateTransferStatus: (id: string, status: string) => request(`/api/v1/referrals/transfers/${id}/status`, { method: "POST", body: JSON.stringify({ status }) }),
  listQueues: () => request("/api/v1/appointments/queues"),
  listQueueEntries: (queueId?: string) => request(`/api/v1/appointments/queues/entries${queueId ? `?queue_id=${queueId}` : ""}`),
  updateQueueEntryStatus: (entryId: string, newStatus: string) => request(`/api/v1/appointments/queues/entries/${entryId}/${newStatus}`, { method: "PATCH" }),

  listMedications: () => request("/api/v1/pharmacy/medications"),
  createMedication: (payload: any) => request("/api/v1/pharmacy/medications", { method: "POST", body: JSON.stringify(payload) }),
  listPharmacyInventory: () => request("/api/v1/pharmacy/inventory"),
  listPrescriptions: (status?: string) => request(`/api/v1/pharmacy/prescriptions${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  receiveInventory: (payload: any) => request("/api/v1/pharmacy/inventory/receive", { method: "POST", body: JSON.stringify(payload) }),

  listBillingServices: () => request("/api/v1/billing/services"),
  createBillingService: (payload: any) => request("/api/v1/billing/services", { method: "POST", body: JSON.stringify(payload) }),
  listInvoices: () => request("/api/v1/billing/invoices"),
  createInvoice: (encounterId: string) => request(`/api/v1/billing/encounters/${encounterId}/invoice`, { method: "POST", body: JSON.stringify({}) }),
  recordPayment: (payload: any, idempotencyKey?: string) => request("/api/v1/billing/payments", { method: "POST", headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined, body: JSON.stringify(payload) }),
  listClaims: () => request("/api/v1/claims"),
  createClaim: (invoice_id: string) => request("/api/v1/claims", { method: "POST", body: JSON.stringify({ invoice_id }) }),
  claimPreflight: (invoice_id: string) => request(`/api/v1/claims/invoices/${invoice_id}/preflight`),
  claimsKesAtRisk: (days = 7) => request(`/api/v1/claims/risk/kes-at-risk?days=${days}`),
  validateClaim: (claim_id: string) => request(`/api/v1/claims/${claim_id}/validate`, { method: "POST" }),
  submitClaim: (claim_id: string) => request(`/api/v1/claims/${claim_id}/submit`, { method: "POST" }),
  listClaimRejections: () => request("/api/v1/claims/workbench/rejections"),
  recordClaimResponse: (claim_id: string, payload: any) => request(`/api/v1/claims/${claim_id}/response`, { method: "POST", body: JSON.stringify(payload) }),
  reconcileClaim: (claim_id: string, received_amount: number) => request(`/api/v1/claims/${claim_id}/reconcile`, { method: "POST", body: JSON.stringify({ received_amount }) }),
  sandboxRejectClaim: (claim_id: string) => request(`/api/v1/claims/${claim_id}/sandbox-reject`, { method: "POST", body: JSON.stringify({}) }),

  listLabTests: () => request("/api/v1/laboratory/tests"),
  createLabOrder: (payload: any) => request("/api/v1/laboratory/orders", { method: "POST", body: JSON.stringify(payload) }),
  getLabOrder: (id: string) => request(`/api/v1/laboratory/orders/${id}`),
  collectLabSample: (lab_order_item_id: string) => request("/api/v1/laboratory/samples/collect", { method: "POST", body: JSON.stringify({ lab_order_item_id }) }),
  receiveLabSample: (sample_id: string) => request("/api/v1/laboratory/samples/receive", { method: "POST", body: JSON.stringify({ sample_id }) }),
  enterLabResult: (payload: any) => request("/api/v1/laboratory/results", { method: "POST", body: JSON.stringify(payload) }),
  verifyLabResult: (result_id: string) => request(`/api/v1/laboratory/results/${result_id}/verify`, { method: "POST" }),
  forwardLabOrder: (order_id: string) => request(`/api/v1/laboratory/orders/${order_id}/forward-to-prescription`, { method: "POST" }),

  listActiveCoverage: (personId: string) => request(`/api/v1/coverage/facility/person/${personId}/active`),
  listPayers: () => request("/api/v1/coverage/payers"),
  listPayerPlans: (payerId: string) => request(`/api/v1/coverage/payers/${payerId}/plans`),
  createCoverage: (payload: any) => request("/api/v1/coverage", { method: "POST", body: JSON.stringify(payload) }),
  verifyCoverage: (coverageId: string) => request(`/api/v1/coverage/${coverageId}/verify`, { method: "POST" }),
  adjudicateBenefit: (payload: any) => request("/api/v1/coverage/adjudicate", { method: "POST", body: JSON.stringify(payload) }),
  simulateCoverage: (payload: any) => request("/api/v1/coverage/adjudicate", { method: "POST", body: JSON.stringify(payload) }),

  commandCentre: () => request("/api/v1/command-centre"),
  fraudRadar: () => request("/api/v1/fraud-radar"),
  allergySafety: (patientId: string, medicationId: string) => request(`/api/v1/patients/${patientId}/allergy-safety/medications/${medicationId}`),
  getFhirPatient: (patientId: string, accessReason: string) => request(`/api/v1/interoperability/Patient/${patientId}?access_reason=${encodeURIComponent(accessReason)}`),
  getFhirAllergies: (patientId: string, accessReason: string, includeInactive = true) => request(`/api/v1/interoperability/AllergyIntolerance/${patientId}?access_reason=${encodeURIComponent(accessReason)}&include_inactive=${includeInactive}`),

  portalContinuityCards: () => request("/api/v1/portal/continuity-card"),
  portalIssueContinuityCard: () => request("/api/v1/portal/continuity-card/issue", { method: "POST", body: JSON.stringify({}) }),
  portalRevokeContinuityCard: (id: string) => request(`/api/v1/portal/continuity-card/${id}/revoke`, { method: "POST", body: JSON.stringify({}) }),
  continuityVerify: (token: string) => request("/api/v1/continuity/verify", { method: "POST", body: JSON.stringify({ token }) }, false),
  facilityContinuityScan: (token: string) => request("/api/v1/facility/continuity/scan", { method: "POST", body: JSON.stringify({ token }) }),
  offlineStats: () => request("/api/v1/offline/stats"),
  offlinePending: (limit = 50) => request(`/api/v1/offline/pending?limit=${limit}`),
  offlineEnqueue: (payload: any) => request("/api/v1/offline/enqueue", { method: "POST", body: JSON.stringify(payload) }),
  offlineDrain: (limit = 25) => request(`/api/v1/offline/drain?limit=${limit}`, { method: "POST" }),
  offlineProbe: (target: string, ok: boolean, latency_ms?: number, detail?: string) => request("/api/v1/offline/connectivity-probe", { method: "POST", body: JSON.stringify({ target, ok, latency_ms, detail }) }),
  identityHouseholds: (search = "") => request(`/api/v1/identity/households${search.trim() ? `?search=${encodeURIComponent(search.trim())}` : ""}`),
  identityHousehold: (id: string) => request(`/api/v1/identity/households/${id}`),
  createHousehold: (payload: any) => request("/api/v1/identity/households", { method: "POST", body: JSON.stringify(payload) }),
  addHouseholdMember: (householdId: string, payload: any) => request(`/api/v1/identity/households/${householdId}/members`, { method: "POST", body: JSON.stringify(payload) }),
  personMemberships: (personId: string) => request(`/api/v1/identity/memberships/person/${personId}`),
  createMembership: (payload: any) => request("/api/v1/identity/memberships", { method: "POST", body: JSON.stringify(payload) }),
  addContribution: (payload: any) => request("/api/v1/identity/contributions", { method: "POST", body: JSON.stringify(payload) }),
  citizenWalletOverview: () => request("/api/v1/citizen-wallet/overview"),
  citizenWalletBenefits: () => request("/api/v1/citizen-wallet/benefits"),
  citizenWalletCharges: (limit = 50) => request(`/api/v1/citizen-wallet/charges?limit=${limit}`),
  securityAccessReview: (days = 7, limit = 100) => request(`/api/v1/security-ops/access-review?days=${days}&limit=${limit}`),
  securityPrivacySummary: (days = 30) => request(`/api/v1/security-ops/privacy-summary?days=${days}`),
  securityChecklist: () => request("/api/v1/security-ops/checklist"),
  staffList: (limit = 200, offset = 0, status = "ACTIVE") => request(`/api/v1/staff?limit=${limit}&offset=${offset}&status=${status}`),
  workforceCompliance: (daysAhead = 60) => request(`/api/v1/workforce/compliance?days_ahead=${daysAhead}`),
  workforceStaffCheck: (staffId: string) => request(`/api/v1/workforce/staff/${staffId}/check`),
  workforceCredentialCreate: (payload: any) => request("/api/v1/workforce/credentials", { method: "POST", body: JSON.stringify(payload) }),
  onboardingFacilityKit: () => request("/api/v1/onboarding/facility-kit"),
  onboardingMigrationPlaybook: () => request("/api/v1/onboarding/migration-playbook"),
  trainingSops: (audience = "") => request(`/api/v1/training/sops${audience ? `?audience=${encodeURIComponent(audience)}` : ""}`),
  trainingModules: () => request("/api/v1/training/modules"),
  trainingHelp: (q = "") => request(`/api/v1/training/help${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  trainingCatalog: () => request("/api/v1/training/catalog"),
  rolloutCountyDashboard: (limit = 50) => request(`/api/v1/rollout/county-dashboard?limit=${limit}`),
  rolloutPilotEvidence: (includeFacility = false) => request(`/api/v1/rollout/pilot-evidence?include_facility=${includeFacility}`),
  warehouseFacts: (days = 30) => request(`/api/v1/warehouse/facts?days=${days}`),
  warehouseCountyFacts: (days = 30) => request(`/api/v1/warehouse/county-facts?days=${days}`),
  warehouseCatalog: () => request("/api/v1/warehouse/catalog"),
  certificationSubmissionKit: () => request("/api/v1/certification/submission-kit"),
  productionReadiness: () => request("/api/v1/production/readiness"),
  productionDeployChecklist: () => request("/api/v1/production/deploy-checklist"),
  observabilityRuntime: () => request("/api/v1/observability/runtime"),
  observabilitySlos: () => request("/api/v1/observability/slos"),
  observabilityTracingHooks: () => request("/api/v1/observability/tracing-hooks"),
  partnerSandboxContracts: () => request("/api/v1/partner-sandbox/contracts"),
  drChecklist: () => request("/api/v1/dr/checklist"),
  changePolicy: () => request("/api/v1/change-control/policy"),
  pilotHandoverEvidence: (county = "", facilityId = "") => request(`/api/v1/pilot-handover/evidence-pack${county || facilityId ? `?${county ? `county=${encodeURIComponent(county)}` : ""}${county && facilityId ? "&" : ""}${facilityId ? `facility_id=${encodeURIComponent(facilityId)}` : ""}` : ""}`),
  pilotCountyHandover: (county: string) => request(`/api/v1/pilot-handover/county-handover?county=${encodeURIComponent(county)}`),
  performanceCatalogue: () => request("/api/v1/performance/catalogue"),
  performanceAcceptance: () => request("/api/v1/performance/acceptance"),
  riskPosture: () => request("/api/v1/risk-register/posture"),
  riskList: (status = "", category = "") => request(`/api/v1/risk-register/risks?limit=200${status ? `&status=${encodeURIComponent(status)}` : ""}${category ? `&category=${encodeURIComponent(category)}` : ""}`),
  riskUpdate: (id: string, payload: any) => request(`/api/v1/risk-register/risks/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  changeList: (limit = 200) => request(`/api/v1/change-control/changes?limit=${limit}`),
  changeCreate: (payload: any) => request("/api/v1/change-control/changes", { method: "POST", body: JSON.stringify(payload) }),
  changeTransition: (id: string, payload: any) => request(`/api/v1/change-control/changes/${id}/transition`, { method: "POST", body: JSON.stringify(payload) }),
  changeReleases: (limit = 100) => request(`/api/v1/change-control/releases?limit=${limit}`),
  changeRelease: (payload: any) => request("/api/v1/change-control/releases", { method: "POST", body: JSON.stringify(payload) }),
  drPosture: () => request("/api/v1/dr/posture"),
  drBackups: (limit = 50) => request(`/api/v1/dr/backups?limit=${limit}`),
  drRecordBackup: (payload: any) => request("/api/v1/dr/backups", { method: "POST", body: JSON.stringify(payload) }),
  drDrills: (limit = 50) => request(`/api/v1/dr/drills?limit=${limit}`),
  drStartDrill: (payload: any) => request("/api/v1/dr/drills", { method: "POST", body: JSON.stringify(payload) }),
  drCompleteDrill: (id: string, payload: any) => request(`/api/v1/dr/drills/${id}/complete`, { method: "POST", body: JSON.stringify(payload) }),
  partnerSandboxEligibility: (payload: any) => request("/api/v1/partner-sandbox/eligibility", { method: "POST", body: JSON.stringify(payload) }),
  partnerSandboxClaimPreflight: (payload: any) => request("/api/v1/partner-sandbox/claim-preflight", { method: "POST", body: JSON.stringify(payload) }),
  partnerSandboxHieEcho: (payload: any) => request("/api/v1/partner-sandbox/hie-echo", { method: "POST", body: JSON.stringify(payload) }),
  partnerSandboxRegisterInterest: (payload: any) => request("/api/v1/partner-sandbox/register-interest", { method: "POST", body: JSON.stringify(payload) }),
  retentionPolicies: () => request("/api/v1/retention/policies"),
  retentionRequests: (status = "", limit = 50) => request(`/api/v1/retention/requests?limit=${limit}${status ? `&status=${encodeURIComponent(status)}` : ""}`),
  createRetentionRequest: (payload: any) => request("/api/v1/retention/requests", { method: "POST", body: JSON.stringify(payload) }),
  decideRetentionRequest: (id: string, payload: any) => request(`/api/v1/retention/requests/${id}/decide`, { method: "POST", body: JSON.stringify(payload) }),
};

export async function downloadWarehouseCsv(days = 30): Promise<string> {
  const headers = new Headers();
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${API_BASE}/api/v1/warehouse/export/county-facts.csv?days=${days}`, { headers });
  if (!res.ok) throw new ApiError(res.status, "CSV_EXPORT_FAILED");
  return res.text();
}

export const api: any = { ..._apiCore, ...citizenApiMethods(request) };
