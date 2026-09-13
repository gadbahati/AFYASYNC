import type { NationalReport } from "./types";
import { getAccessToken } from "../auth/storage";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export async function getNationalReport(start?: string, end?: string): Promise<NationalReport> {
  if (!API_BASE && import.meta.env.PROD) throw new Error("API_NOT_CONFIGURED");
  const query = new URLSearchParams();
  if (start) query.set("start_date", start);
  if (end) query.set("end_date", end);
  const token = getAccessToken();
  const response = await fetch(`${API_BASE}/api/v1/reports/national${query.toString() ? `?${query}` : ""}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok) {
    let code = "NATIONAL_REPORT_LOAD_FAILED";
    try {
      const body = await response.json() as { detail?: string | { code?: string } };
      if (typeof body.detail === "string") code = body.detail;
      else if (body.detail?.code) code = body.detail.code;
    } catch {}
    throw new Error(code);
  }
  return response.json() as Promise<NationalReport>;
}
