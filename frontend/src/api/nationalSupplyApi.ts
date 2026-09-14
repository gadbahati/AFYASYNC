import type { NationalSupplyResponse } from "./nationalSupply";
import { getAccessToken } from "../auth/storage";

const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;

function apiBase() {
  if (!baseUrl || baseUrl.includes("localhost") || baseUrl.includes("127.0.0.1")) {
    throw new Error("API_BASE_URL_NOT_CONFIGURED");
  }
  return baseUrl.replace(/\/$/, "");
}

export async function getNationalSupply(params: {
  county?: string;
  medicationCode?: string;
  lowStockOnly?: boolean;
  limit?: number;
  offset?: number;
} = {}): Promise<NationalSupplyResponse> {
  const query = new URLSearchParams();
  if (params.county?.trim()) query.set("county", params.county.trim());
  if (params.medicationCode?.trim()) query.set("medication_code", params.medicationCode.trim());
  if (params.lowStockOnly) query.set("low_stock_only", "true");
  query.set("limit", String(params.limit ?? 100));
  query.set("offset", String(params.offset ?? 0));

  const token = getAccessToken();
  if (!token) throw new Error("AUTH_REQUIRED");
  const response = await fetch(`${apiBase()}/api/v1/national/supply/inventory?${query.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    let detail = "NATIONAL_SUPPLY_REQUEST_FAILED";
    try { const body = await response.json(); detail = typeof body.detail === "string" ? body.detail : detail; } catch { /* non-JSON error */ }
    throw new Error(detail);
  }
  return response.json() as Promise<NationalSupplyResponse>;
}
