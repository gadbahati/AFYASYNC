export type NationalReferralItem = {
  id: string;
  referral_id: string;
  source_facility_id: string;
  source_facility_code: string;
  source_facility_name: string;
  source_county: string | null;
  destination_facility_id: string;
  destination_facility_code: string;
  destination_facility_name: string;
  destination_county: string | null;
  destination_department_id: string | null;
  destination_department_name: string | null;
  priority: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type NationalReferralResponse = {
  items: NationalReferralItem[];
  total: number;
  limit: number;
  offset: number;
  status_counts: { status: string; count: number }[];
  priority_counts: { priority: string; count: number }[];
};
