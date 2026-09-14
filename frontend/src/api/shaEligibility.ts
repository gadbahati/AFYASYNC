export type SHAEligibilityResponse = {
  coverage_id: string | null;
  person_id: string;
  payer_id: string;
  payer_plan_id: string | null;
  membership_number: string;
  eligible: boolean;
  verification_status: string;
  start_date: string | null;
  end_date: string | null;
  external_reference: string | null;
  checked_at: string;
};
