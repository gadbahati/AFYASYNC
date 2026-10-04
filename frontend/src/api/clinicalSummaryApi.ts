/** Phase 137 — clinical summary client helper. Developed by BAHATI GAD WANGWE */
export function bindClinicalSummaryMethods(
  api: any,
  request: (path: string, init?: RequestInit) => Promise<any>,
) {
  api.getEncounterSummary = (encounterId: string) =>
    request(`/api/v1/encounters/${encounterId}/summary`);
  return api;
}
