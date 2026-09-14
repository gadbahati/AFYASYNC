import type { SHAEligibilityResponse } from "./shaEligibility";
import { clearSession, getAccessToken, getRefreshToken, setSession } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class SHAEligibilityApiError extends Error {
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
    setSession(await response.json());
    return true;
  } catch { clearSession(); return false; }
}

export async function checkSHAEligibility(personId: string, membershipNumber: string): Promise<SHAEligibilityResponse> {
  const membership = membershipNumber.trim().toUpperCase();
  if (!personId) throw new SHAEligibilityApiError(400, "PERSON_ID_REQUIRED");
  if (!membership) throw new SHAEligibilityApiError(400, "MEMBERSHIP_NUMBER_REQUIRED");
  if (membership.length > 100) throw new SHAEligibilityApiError(422, "MEMBERSHIP_NUMBER_TOO_LONG");
  if (!API_BASE && import.meta.env.PROD) throw new SHAEligibilityApiError(0, "API_NOT_CONFIGURED");

  const headers = new Headers({ "Content-Type": "application/json" });
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/coverage/sha/eligibility`, {
      method: "POST",
      headers,
      body: JSON.stringify({ person_id: personId, membership_number: membership }),
    });
  } catch { throw new SHAEligibilityApiError(0, "API_UNREACHABLE"); }

  if (response.status === 401) {
    if (!refreshPromise) refreshPromise = refresh().finally(() => { refreshPromise = null; });
    if (await refreshPromise) return checkSHAEligibility(personId, membership);
  }
  if (!response.ok) {
    let code = "SHA_ELIGIBILITY_REQUEST_FAILED";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") code = body.detail;
      else if (body.detail?.code) code = body.detail.code;
    } catch { /* preserve generic code */ }
    throw new SHAEligibilityApiError(response.status, code);
  }
  return await response.json() as SHAEligibilityResponse;
}
