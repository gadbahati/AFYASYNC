/** Phase 138 — clinical client path contract. Developed by BAHATI GAD WANGWE */

export function bindClinicalExtras(
  api: any,
  request: (path: string, init?: RequestInit) => Promise<any>,
) {
  // Timeline: prefer clinical-timeline; /clinical remains as backend alias
  api.getClinicalTimeline = (encounterId: string) =>
    request(`/api/v1/encounters/${encounterId}/clinical-timeline`);

  // Notes: prefer /notes; /clinical-notes remains as backend alias
  api.getClinicalNotes = (encounterId: string) =>
    request(`/api/v1/encounters/${encounterId}/notes`);
  api.addClinicalNote = (encounterId: string, payload: any) =>
    request(`/api/v1/encounters/${encounterId}/notes`, {
      method: "POST",
      body: JSON.stringify(payload),
    });

  api.getEncounterSummary = (encounterId: string) =>
    request(`/api/v1/encounters/${encounterId}/summary`);

  api.closeEncounter = (encounterId: string) =>
    request(`/api/v1/encounters/${encounterId}/close`, { method: "POST" });

  api.forwardClinicalOrder =
    api.forwardClinicalOrder ||
    ((orderId: string) =>
      request(`/api/v1/encounters/orders/${orderId}/forward`, { method: "POST" }));

  return api;
}
