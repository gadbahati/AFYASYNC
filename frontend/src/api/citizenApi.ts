/** Afya Citizen portal API methods — attached to main api client. */

type RequestFn = <T = any>(path: string, init?: RequestInit, retry?: boolean) => Promise<T>;

export function citizenApiMethods(request: RequestFn) {
  return {
    citizenTimeline: () => request("/api/v1/portal/citizen/timeline"),
    citizenAccessHistory: () => request("/api/v1/portal/citizen/access-history"),
    citizenCharges: () => request("/api/v1/portal/citizen/charges"),
    citizenEmergency: () => request("/api/v1/portal/citizen/emergency-summary"),
    citizenDocuments: () => request("/api/v1/portal/citizen/documents"),
    citizenComplaints: () => request("/api/v1/portal/citizen/complaints"),
    citizenCreateComplaint: (payload: any) =>
      request("/api/v1/portal/citizen/complaints", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
  };
}
