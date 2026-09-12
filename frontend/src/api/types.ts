export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type FacilityOption = {
  facility_id: string;
  facility_name: string;
};

export type FacilitySelectionRequired = {
  requires_facility_selection: true;
  access_token: string;
  facilities: FacilityOption[];
};

export type LoginResult = TokenResponse | FacilitySelectionRequired;

export type AuthMe = {
  success: boolean;
  data: { user_id: string; username: string; status: string };
  message: string;
};

export type Patient = {
  id: string;
  afya_id: string;
  first_name: string;
  middle_name: string | null;
  last_name: string;
  date_of_birth: string | null;
  sex: string | null;
  phone: string | null;
  email: string | null;
  address?: string | null;
  status: string;
};

export type PatientListResponse = {
  items: Patient[];
  total: number;
  limit: number;
  offset: number;
};

export type PatientCreate = {
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  date_of_birth?: string | null;
  sex?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
};

export type FacilityReport = {
  facility_id: string;
  start_date: string;
  end_date: string;
  patients: number;
  encounters: number;
  charges_total: string;
  invoices_total: string;
  payer_billed: string;
  patient_billed: string;
  confirmed_payments: string;
  claims: number;
  claims_amount: string;
  claims_approved: string;
  claims_paid: string;
};

export type ApiErrorBody = {
  detail?: string | { code?: string; message?: string };
};
