import { api, ApiError } from "./client";

/** Rejection workbench + sandbox reject — extends claims client surface. */
export async function listClaimRejections() {
  // Prefer dedicated method when present on api object
  const anyApi = api as typeof api & {
    listClaimRejections?: () => Promise<any[]>;
    sandboxRejectClaim?: (id: string, payload: object) => Promise<any>;
  };
  if (typeof anyApi.listClaimRejections === "function") {
    return anyApi.listClaimRejections();
  }
  // Direct path (works even if client object not yet extended)
  const { getAccessToken } = await import("../auth/storage");
  const base = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
  const headers: Record<string, string> = {};
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${base}/api/v1/claims/workbench/rejections`, { headers });
  if (!res.ok) throw new ApiError(res.status, "REJECTIONS_LOAD_FAILED");
  return res.json();
}

export async function sandboxRejectClaim(
  claimId: string,
  payload: { response_code?: string; response_message?: string; external_reference?: string } = {},
) {
  const anyApi = api as typeof api & {
    sandboxRejectClaim?: (id: string, payload: object) => Promise<any>;
  };
  if (typeof anyApi.sandboxRejectClaim === "function") {
    return anyApi.sandboxRejectClaim(claimId, payload);
  }
  const { getAccessToken } = await import("../auth/storage");
  const base = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${base}/api/v1/claims/${claimId}/sandbox-reject`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let code = "SANDBOX_REJECT_FAILED";
    try {
      const body = await res.json();
      code = typeof body.detail === "string" ? body.detail : code;
    } catch { /* ignore */ }
    throw new ApiError(res.status, code);
  }
  return res.json();
}
