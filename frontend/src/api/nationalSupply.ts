export type NationalSupplyItem = {
  facility_id: string;
  facility_code: string;
  facility_name: string;
  county: string | null;
  medication_id: string;
  medication_code: string;
  medication_name: string;
  generic_name: string | null;
  current_quantity: number;
  minimum_quantity: number;
  low_stock: boolean;
  non_expired_batch_quantity: number;
  expiring_within_30_days_quantity: number;
  next_expiry_date: string | null;
};

export type NationalSupplyResponse = {
  items: NationalSupplyItem[];
  total: number;
  limit: number;
  offset: number;
};
