export type SupplyDonor = {
  facility_id: string;
  facility_code: string;
  facility_name: string;
  county: string | null;
  available_surplus: number;
};

export type SupplyReplenishmentRecommendation = {
  facility_id: string;
  facility_code: string;
  facility_name: string;
  county: string | null;
  medication_id: string;
  medication_code: string;
  medication_name: string;
  current_quantity: number;
  minimum_quantity: number;
  shortage_quantity: number;
  suggested_transfer_quantity: number;
  donors: SupplyDonor[];
};

export type SupplyPlanningResponse = {
  recommendations: SupplyReplenishmentRecommendation[];
  total_recommendations: number;
  generated_from_live_inventory: boolean;
};
