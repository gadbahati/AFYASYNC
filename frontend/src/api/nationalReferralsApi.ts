import { getAccessToken } from "../auth/storage";
import type { NationalReferralResponse } from "./nationalReferrals";

const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;

function apiBase() {
  if (!baseUrl || baseUrl.includes("localhost") || baseUrl.includes("127.0.0.1")) throw new Error("API_BASE_URL_NOT_CONFIGURED");
  return baseUrl.replace(/\/$/, "");
}

export async function getNationalReferrals(params: {
  county?: string;
  status?: string;
  priority?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
  offset?: number;
} = {}): Promise<NationalReferralResponse> {
  const query = new URLSearchParams();
  if (params.county?.trim()) query.set("county", params.county.trim());
  if (params.status?.trim()) query.set("status", params.status.trim());
  if (params.priority?.trim()) query.set("priority", params.priority.trim());
  if (params.startDate) query.set("start_date", params.startDate);
  if (params.endDate) query.set("end_date", params.endDate);
  query.set("limit", String(params.limit ?? 100));
  query.set("offset", String(params.offset ?? 0));
  const token = getAccessToken();
  if (!token) throw new Error("AUTH_REQUIRED");
  const response = await fetch(`${apiBase()}/api/v1/national/referrals/overview?${query.toString()}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) {
    let detail = "NATIONAL_REFERRAL_REQUEST_FAILED";
    try { const body = await response.json(); detail = typeof body.detail === "string" ? body.detail : detail; } catch { /* non-JSON error */ }
    throw new Error(detail);
  }
  return response.json() as Promise<NationalReferralResponse>;
}
