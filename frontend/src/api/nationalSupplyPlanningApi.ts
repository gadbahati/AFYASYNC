import { getAccessToken } from "../auth/storage";
import type { SupplyPlanningResponse } from "./nationalSupplyPlanning";

const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;

function apiBase() {
  if (!baseUrl || baseUrl.includes("localhost") || baseUrl.includes("127.0.0.1")) throw new Error("API_BASE_URL_NOT_CONFIGURED");
  return baseUrl.replace(/\/$/, "");
}

export async function getNationalSupplyPlanning(params: { county?: string; medicationCode?: string; limit?: number } = {}): Promise<SupplyPlanningResponse> {
  const token = getAccessToken();
  if (!token) throw new Error("AUTH_REQUIRED");
  const query = new URLSearchParams();
  if (params.county?.trim()) query.set("county", params.county.trim());
  if (params.medicationCode?.trim()) query.set("medication_code", params.medicationCode.trim());
  query.set("limit", String(Math.min(Math.max(params.limit ?? 100, 1), 200)));
  const response = await fetch(`${apiBase()}/api/v1/national/supply/planning?${query.toString()}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) {
    let detail = "NATIONAL_SUPPLY_PLANNING_FAILED";
    try { const body = await response.json(); if (typeof body.detail === "string") detail = body.detail; } catch { /* non-JSON response */ }
    throw new Error(detail);
  }
  return response.json() as Promise<SupplyPlanningResponse>;
}
