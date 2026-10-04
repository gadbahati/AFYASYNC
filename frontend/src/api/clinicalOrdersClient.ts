/** Phase 132–133 clinical orders client helpers. Developed by BAHATI GAD WANGWE */

/** Bind clinical order methods onto the shared api object after client load. */
export function bindClinicalOrderMethods(api: any, request: (path: string, init?: RequestInit) => Promise<any>) {
  api.listClinicalOrders = (encounterId: string, orderType?: string) => {
    const q = orderType ? `?order_type=${encodeURIComponent(orderType)}` : "";
    return request(`/api/v1/encounters/${encounterId}/orders${q}`);
  };
  api.createClinicalOrder = (encounterId: string, payload: any) =>
    request(`/api/v1/encounters/${encounterId}/orders`, { method: "POST", body: JSON.stringify(payload) });
  api.fulfillClinicalOrder = (orderId: string, payload: { status?: string; result_notes?: string } = {}) =>
    request(`/api/v1/encounters/orders/${orderId}/fulfill`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  api.updateClinicalOrderStatus = (orderId: string, status: string) =>
    request(`/api/v1/encounters/orders/${orderId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  api.dischargeEncounterClinical = (encounterId: string, payload: any) =>
    request(`/api/v1/encounters/${encounterId}/discharge`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  return api;
}
