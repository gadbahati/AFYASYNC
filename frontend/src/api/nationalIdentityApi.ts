import type { NationalIdentityResolution } from "./nationalIdentity";
import type { NationalRecordLocatorResponse } from "./nationalRecordLocator";
import { clearSession, getAccessToken, getRefreshToken, setSession } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
export class NationalIdentityApiError extends Error { constructor(public readonly status: number, public readonly code: string) { super(code); } }
let refreshPromise: Promise<boolean> | null = null;

async function refresh(): Promise<boolean> {
  const token = getRefreshToken(); if (!token) return false;
  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: token }) });
    if (!response.ok) { clearSession(); return false; }
    setSession(await response.json() as { access_token: string; refresh_token: string }); return true;
  } catch { clearSession(); return false; }
}
async function request(path: string, init?: RequestInit): Promise<Response> {
  if (!API_BASE && import.meta.env.PROD) throw new NationalIdentityApiError(0, "API_NOT_CONFIGURED");
  const headers = new Headers(init?.headers); const token = getAccessToken(); if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response; try { response = await fetch(`${API_BASE}${path}`, { ...init, headers }); } catch { throw new NationalIdentityApiError(0, "API_UNREACHABLE"); }
  if (response.status === 401 && !refreshPromise) refreshPromise = refresh().finally(() => { refreshPromise = null; });
  if (response.status === 401 && refreshPromise && await refreshPromise) return request(path, init);
  return response;
}
async function parseError(response: Response, fallback: string): Promise<never> {
  let code = fallback; try { const body = await response.json() as { detail?: string | { code?: string } }; if (typeof body.detail === "string") code = body.detail; else if (body.detail?.code) code = body.detail.code; } catch {}
  throw new NationalIdentityApiError(response.status, code);
}
export async function resolveNationalIdentity(afyaId: string, accessReason: string): Promise<NationalIdentityResolution> {
  const normalized = afyaId.trim().toUpperCase(); const reason = accessReason.trim();
  if (!normalized) throw new NationalIdentityApiError(400, "AFYA_ID_REQUIRED");
  if (!/^AF-\d{8}$/.test(normalized)) throw new NationalIdentityApiError(422, "INVALID_AFYA_ID");
  if (reason.length < 5) throw new NationalIdentityApiError(400, "ACCESS_REASON_REQUIRED");
  if (reason.length > 500) throw new NationalIdentityApiError(422, "ACCESS_REASON_TOO_LONG");
  const response = await request(`/api/v1/national/identity/resolve?afya_id=${encodeURIComponent(normalized)}&access_reason=${encodeURIComponent(reason)}`);
  if (!response.ok) return parseError(response, "NATIONAL_IDENTITY_REQUEST_FAILED"); return await response.json() as NationalIdentityResolution;
}
export async function locateNationalRecords(afyaId: string, accessReason: string): Promise<NationalRecordLocatorResponse> {
  const normalized = afyaId.trim().toUpperCase(); const reason = accessReason.trim();
  if (!normalized) throw new NationalIdentityApiError(400, "AFYA_ID_REQUIRED");
  if (!/^AF-\d{8}$/.test(normalized)) throw new NationalIdentityApiError(422, "INVALID_AFYA_ID");
  if (reason.length < 5) throw new NationalIdentityApiError(400, "ACCESS_REASON_REQUIRED");
  if (reason.length > 500) throw new NationalIdentityApiError(422, "ACCESS_REASON_TOO_LONG");
  const response = await request("/api/v1/national/identity/locate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ afya_id: normalized, access_reason: reason }) });
  if (!response.ok) return parseError(response, "NATIONAL_RECORD_LOCATOR_FAILED"); return await response.json() as NationalRecordLocatorResponse;
}
