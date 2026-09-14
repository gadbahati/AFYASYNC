import { getAccessToken } from "../auth/storage";
import type { NationalReferralMetrics, NationalReferralResponse } from "./nationalReferrals";

const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;

function apiBase() {
  if (!baseUrl || baseUrl.includes("localhost") || baseUrl.includes("127.0.0.1")) throw new Error("API_BASE_URL_NOT_CONFIGURED");
  return baseUrl.replace(/\/$/, "");
}

async function request(path: string): Promise<unknown> {
  const token = getAccessToken();
  if (!token) throw new Error("AUTH_REQUIRED");
  const response = await fetch(`${apiBase()}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) {
    let detail = "NATIONAL_REFERRAL_REQUEST_FAILED";
    try { const body = await response.json(); detail = typeof body.detail === "string" ? body.detail : detail; } catch { /* non-JSON error */ }
    throw new Error(detail);
  }
  return response.json();
}

function validOverview(value: unknown): value is NationalReferralResponse {
  if (!value || typeof value !== "object") return false;
  const data = value as NationalReferralResponse;
  return Array.isArray(data.items) && Number.isInteger(data.total) && Number.isInteger(data.limit) && Number.isInteger(data.offset) && Array.isArray(data.status_counts) && Array.isArray(data.priority_counts);
}

function validMetrics(value: unknown): value is NationalReferralMetrics {
  if (!value || typeof value !== "object") return false;
  const data = value as NationalReferralMetrics;
  return Number.isInteger(data.total) && Number.isInteger(data.active) && Number.isInteger(data.completed) && Number.isInteger(data.declined) && Number.isFinite(data.acceptance_rate) && Number.isFinite(data.completion_rate) && Array.isArray(data.aging) && Array.isArray(data.routes);
}

export async function getNationalReferrals(params: { county?: string; status?: string; priority?: string; startDate?: string; endDate?: string; limit?: number; offset?: number } = {}): Promise<NationalReferralResponse> {
  const query = new URLSearchParams();
  if (params.county?.trim()) query.set("county", params.county.trim());
  if (params.status?.trim()) query.set("status", params.status.trim());
  if (params.priority?.trim()) query.set("priority", params.priority.trim());
  if (params.startDate) query.set("start_date", params.startDate);
  if (params.endDate) query.set("end_date", params.endDate);
  query.set("limit", String(params.limit ?? 100));
  query.set("offset", String(params.offset ?? 0));
  const value = await request(`/api/v1/national/referrals/overview?${query.toString()}`);
  if (!validOverview(value)) throw new Error("INVALID_NATIONAL_REFERRAL_RESPONSE");
  return value;
}

export async function getNationalReferralMetrics(params: { county?: string; startDate?: string; endDate?: string } = {}): Promise<NationalReferralMetrics> {
  const query = new URLSearchParams();
  if (params.county?.trim()) query.set("county", params.county.trim());
  if (params.startDate) query.set("start_date", params.startDate);
  if (params.endDate) query.set("end_date", params.endDate);
  const value = await request(`/api/v1/national/referrals/metrics?${query.toString()}`);
  if (!validMetrics(value)) throw new Error("INVALID_NATIONAL_REFERRAL_METRICS_RESPONSE");
  return value;
}
