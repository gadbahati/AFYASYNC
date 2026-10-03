/** Phase 108 — settlement & claims financing client helpers.
 *  Developed by BAHATI GAD WANGWE
 */
import { api } from "./client";

export function settlementCreateObligation(claimId: string) {
  return api.settlementCreateObligation(claimId);
}

export function settlementCreateBatch(payerId: string) {
  return api.settlementCreateBatch(payerId);
}

export function settlementRecordPayment(payload: {
  obligation_id: string;
  amount: number;
  method?: string;
}) {
  return api.settlementRecordPayment(payload);
}

export function settlementReconcile(payload: {
  batch_id: string;
  received_amount: number;
}) {
  return api.settlementReconcile(payload);
}

export function settlementListBatches() {
  return api.settlementListBatches();
}
