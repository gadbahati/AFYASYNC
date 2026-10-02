import {api} from "../api/client";
export async function loadContractRenewal(days=180){return api.tariffIntelligence?api.contractRenewalIntelligence(days):fetch((import.meta.env.VITE_API_URL||"")+"/api/v1/contract-renewal?days="+days).then(r=>r.json())}
