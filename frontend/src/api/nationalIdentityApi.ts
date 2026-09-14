import type { NationalIdentityResolution } from "./nationalIdentity";
import { clearSession, getAccessToken, getRefreshToken, setSession } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class NationalIdentityApiError extends Error {
  constructor(public readonly status: number, public readonly code: string) {
    super(code);
  }
}

let refreshPromise: Promise<boolean> | null = null;

async function refresh(): Promise<boolean> {
  const token = getRefreshToken();
  if (!token) return false;
  try {
    const response = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: token }),
    });
    if (!response.ok) { clearSession(); return false; }
    const data = await response.json() as { access_token: string; refresh_token: string };
    setSession(data);
    return true;
  } catch { clearSession(); return false; }
}

export async function resolveNationalIdentity(afyaId: string): Promise<NationalIdentityResolution> {
  const normalized = afyaId.trim().toUpperCase();
  if (!normalized) throw new NationalIdentityApiError(400, "AFYA_ID_REQUIRED");
  if (normalized.length > 20) throw new NationalIdentityApiError(422, "AFYA_ID_TOO_LONG");
  if (!API_BASE && import.meta.env.PROD) throw new NationalIdentityApiError(0, "API_NOT_CONFIGURED");

  const headers = new Headers();
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/national/identity/resolve?afya_id=${encodeURIComponent(normalized)}`, { headers });
  } catch {
    throw new NationalIdentityApiError(0, "API_UNREACHABLE");
  }

  if (response.status === 401) {
    if (!refreshPromise) refreshPromise = refresh().finally(() => { refreshPromise = null; });
    if (await refreshPromise) return resolveNationalIdentity(normalized);
  }
  if (!response.ok) {
    let code = "NATIONAL_IDENTITY_REQUEST_FAILED";
    try {
      const body = await response.json() as { detail?: string | { code?: string } };
      if (typeof body.detail === "string") code = body.detail;
      else if (body.detail?.code) code = body.detail.code;
    } catch { /* retain generic code */ }
    throw new NationalIdentityApiError(response.status, code);
  }
  return await response.json() as NationalIdentityResolution;
}
