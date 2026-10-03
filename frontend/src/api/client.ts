import { clearSession, getAccessToken, getAccountType, getRefreshToken, setSession } from "../auth/storage";

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T = any>(path: string, init: RequestInit = {}, auth = true): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (auth) {
    const token = getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(path.startsWith("http") ? path : path, { ...init, headers });
  if (!res.ok) {
    let code = "REQUEST_FAILED";
    let message = res.statusText;
    try {
      const body = await res.json();
      code = body?.detail || body?.code || code;
      message = body?.message || (typeof body?.detail === "string" ? body.detail : message);
    } catch {}
    throw new ApiError(String(code), String(message), res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Temporary bootstrap while full client is restored — critical auth + Phase 90 context. */
const _apiCore: any = {
  contextOverview: (scope?: string) => request("/api/v1/context" + (scope ? `?scope=${encodeURIComponent(scope)}` : "")),
  contextScopeSummary: (scope: string = "facility") =>
    request(`/api/v1/context/scope-summary?scope=${encodeURIComponent(scope)}`),
  login: (username: string, password: string) =>
    request("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }, false),
  patientLogin: (identifier: string, password: string) =>
    request("/api/v1/auth/patient/login", { method: "POST", body: JSON.stringify({ identifier, password }) }, false),
  facilityReport: () => request("/api/v1/reports/facility"),
  listReferrals: (role = "source") => request(`/api/v1/referrals?role=${role}`),
  listTransfers: (role = "source") => request(`/api/v1/transfers?role=${role}`),
};

export const api: any = new Proxy(_apiCore, {
  get(target, prop, receiver) {
    if (prop in target) return Reflect.get(target, prop, receiver);
    return (...args: any[]) => {
      console.warn("api." + String(prop) + " is not in the slim client bootstrap; restore full client.ts");
      return Promise.reject(new ApiError("API_METHOD_MISSING", String(prop), 501));
    };
  },
});

export { request };
