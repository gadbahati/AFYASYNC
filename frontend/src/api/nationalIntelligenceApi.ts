import type { NationalIntelligenceResponse } from "./nationalIntelligence";
import { getAccessToken } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  if (!API_BASE && import.meta.env.PROD) throw new Error("API_NOT_CONFIGURED");
  const headers = new Headers({ Accept: "application/json" });
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { headers, signal });
  if (!response.ok) {
    let code = "NATIONAL_INTELLIGENCE_LOAD_FAILED";
    try {
      const body = await response.json() as { detail?: string | { code?: string } };
      if (typeof body.detail === "string") code = body.detail;
      else if (body.detail?.code) code = body.detail.code;
    } catch {
      // Preserve the generic error when the server did not return JSON.
    }
    throw new Error(code);
  }
  return response.json() as Promise<T>;
}

export async function getNationalIntelligence(start?: string, end?: string, signal?: AbortSignal): Promise<NationalIntelligenceResponse> {
  const q = new URLSearchParams();
  if (start) q.set("start_date", start);
  if (end) q.set("end_date", end);
  return request(`/api/v1/reports/national/intelligence${q.toString() ? `?${q}` : ""}`, signal);
}
