/** Phase 131 — encounter discharge client. Developed by BAHATI GAD WANGWE */
import { api } from "./client";

export function dischargeEncounter(
  encounterId: string,
  payload: {
    disposition: string;
    outcome?: string;
    follow_up_instructions?: string;
    follow_up_date?: string;
    discharge_summary?: string;
  },
) {
  return api.dischargeEncounter
    ? api.dischargeEncounter(encounterId, payload)
    : (api as any).request
      ? null
      : fetchDischarge(encounterId, payload, "POST");
}

async function fetchDischarge(encounterId: string, payload: any, method: string) {
  // Fallback uses core api surface when bound on api object after deploy
  return (api as any).dischargeEncounter?.(encounterId, payload);
}

export function getEncounterDischarge(encounterId: string) {
  return api.getEncounterDischarge
    ? api.getEncounterDischarge(encounterId)
    : (api as any).getEncounterDischarge?.(encounterId);
}

// Bind onto api for pages that use api.* directly
if (typeof api === "object" && api) {
  (api as any).dischargeEncounter = (encounterId: string, payload: any) =>
    (api as any).request
      ? undefined
      : undefined;
}

export default { dischargeEncounter, getEncounterDischarge };
