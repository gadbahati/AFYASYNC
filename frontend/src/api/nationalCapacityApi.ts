import { getAccessToken } from "../auth/storage";
import type { NationalCapacity } from "./nationalCapacity";

const baseUrl = import.meta.env.VITE_API_BASE_URL as string | undefined;

function apiBase() {
  if (!baseUrl || baseUrl.includes("localhost") || baseUrl.includes("127.0.0.1")) throw new Error("API_BASE_URL_NOT_CONFIGURED");
  return baseUrl.replace(/\/$/, "");
}

export async function getNationalCapacity(county?: string): Promise<NationalCapacity> {
  const token = getAccessToken();
  if (!token) throw new Error("AUTH_REQUIRED");
  const query = county?.trim() ? `?county=${encodeURIComponent(county.trim())}` : "";
  const response = await fetch(`${apiBase()}/api/v1/national/capacity/overview${query}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error(response.status === 403 ? "PERMISSION_DENIED" : "NATIONAL_CAPACITY_REQUEST_FAILED");
  const value: unknown = await response.json();
  if (!value || typeof value !== "object") throw new Error("INVALID_NATIONAL_CAPACITY_RESPONSE");
  const data = value as NationalCapacity;
  if (!Number.isInteger(data.active_facilities) || !Number.isInteger(data.active_departments) || !Number.isInteger(data.scheduled_appointments) || !Number.isInteger(data.waiting_queue_entries) || !Array.isArray(data.facilities)) throw new Error("INVALID_NATIONAL_CAPACITY_RESPONSE");
  return data;
}
