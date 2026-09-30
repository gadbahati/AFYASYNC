import { getAccessToken } from "../auth/storage";
const base = import.meta.env.VITE_API_BASE_URL as string | undefined;
export async function createReferralBooking(payload: unknown, idempotencyKey: string) {
  if (!base || base.includes("localhost") || base.includes("127.0.0.1")) throw new Error("API_BASE_URL_NOT_CONFIGURED");
  const token = getAccessToken();
  if (!token) throw new Error("AUTH_REQUIRED");
  const res = await fetch(`${base.replace(/\/$/, "")}/api/v1/referral-booking/book`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}`, "Idempotency-Key": idempotencyKey }, body: JSON.stringify(payload) });
  if (!res.ok) { const body = await res.json().catch(() => ({})); throw new Error(body.detail || "REFERRAL_BOOKING_FAILED"); }
  return res.json();
}
