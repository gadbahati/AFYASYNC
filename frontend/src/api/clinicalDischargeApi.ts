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
  return api.dischargeEncounter(encounterId, payload);
}

export function getEncounterDischarge(encounterId: string) {
  return api.getEncounterDischarge(encounterId);
}

export default { dischargeEncounter, getEncounterDischarge };
