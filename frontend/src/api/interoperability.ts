export type FHIRClinicalSummary = {
  resourceType: "Bundle";
  type: "searchset";
  total: number;
  entry: Array<{
    fullUrl: string;
    resource: {
      resourceType: "Patient" | "Encounter";
      id: string;
      [key: string]: unknown;
    };
  }>;
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

function token(): string {
  return localStorage.getItem("access_token") || localStorage.getItem("token") || "";
}

export async function getClinicalSummary(patientId: string, accessReason: string): Promise<FHIRClinicalSummary> {
  const reason = accessReason.trim();
  if (reason.length < 3 || reason.length > 200) throw new Error("INVALID_ACCESS_REASON");
  const response = await fetch(`${API_BASE}/api/v1/interoperability/Patient/${encodeURIComponent(patientId)}/$summary?access_reason=${encodeURIComponent(reason)}`, {
    headers: { Authorization: `Bearer ${token()}` },
  });
  if (!response.ok) {
    let code = `HTTP_${response.status}`;
    try { const body = await response.json(); if (typeof body?.detail === "string") code = body.detail; } catch { /* preserve HTTP code */ }
    throw new Error(code);
  }
  return response.json();
}
