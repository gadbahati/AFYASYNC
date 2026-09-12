export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type FacilityOption = { facility_id: string; facility_name: string };
export type FacilitySelectionRequired = { requires_facility_selection: true; access_token: string; facilities: FacilityOption[] };
export type LoginResult = TokenResponse | FacilitySelectionRequired;
export type AuthMe = { success: boolean; data: { user_id: string; username: string; status: string }; message: string };

export type Patient = {
  id: string; afya_id: string; first_name: string; middle_name: string | null; last_name: string;
  date_of_birth: string | null; sex: string | null; phone: string | null; email: string | null;
  address?: string | null; status: string;
};
export type PatientListResponse = { items: Patient[]; total: number; limit: number; offset: number };
export type PatientCreate = { first_name: string; middle_name?: string | null; last_name: string; date_of_birth?: string | null; sex?: string | null; phone?: string | null; email?: string | null; address?: string | null };

export type FacilityReport = {
  facility_id: string; start_date: string; end_date: string; patients: number; encounters: number;
  charges_total: string; invoices_total: string; payer_billed: string; patient_billed: string;
  confirmed_payments: string; claims: number; claims_amount: string; claims_approved: string; claims_paid: string;
};
export type BenefitPackage = { id: string; payer_code: string; package_code: string; name: string; description: string; status: string };

export type SHAMember = {
  person_id: string; afya_id: string; membership_number: string; full_name: string;
  date_of_birth: string | null; sex: string | null; coverage_status: string; benefit_package_codes: string[];
};
export type Admission = {
  id: string; admission_number: string; patient_id: string; facility_id: string; encounter_id: string;
  benefit_package_code: string; ward: string; bed: string; diagnosis: string | null; status: string;
  admitted_at: string; discharged_at: string | null;
};

export type Department = { id: string; facility_id: string; name: string; code: string; status: string };
export type Encounter = { id: string; encounter_id: string; patient_id: string; facility_id: string; department_id: string; encounter_type: string; reason: string | null; status: string; started_at: string; ended_at: string | null; created_by: string };
export type EncounterCreate = { patient_id: string; facility_id: string; department_id: string; encounter_type: string; reason?: string | null };
export type Vital = { id: string; encounter_id: string; recorded_by: string; systolic_bp: number | null; diastolic_bp: number | null; pulse: number | null; temperature_c: number | null; respiratory_rate: number | null; oxygen_saturation: number | null; weight_kg: number | null; height_cm: number | null; bmi: number | null; recorded_at: string };
export type Consultation = { id: string; encounter_id: string; doctor_id: string; chief_complaint: string | null; history: string | null; examination: string | null; assessment: string | null; clinical_notes: string | null; treatment_plan: string | null; created_at: string; updated_at: string };
export type Diagnosis = { id: string; encounter_id: string; diagnosis_code: string | null; diagnosis_name: string; diagnosis_type: string; status: string; recorded_by: string; created_at: string };
export type LabOrderSummary = { id: string; order_id: string; encounter_id: string; patient_id: string; priority: string; status: string; created_at: string };
export type PrescriptionSummary = { id: string; prescription_id: string; encounter_id: string; patient_id: string; status: string; created_at: string };
export type ClinicalTimeline = { encounter: Encounter; vitals: Vital[]; consultation: Consultation | null; diagnoses: Diagnosis[]; lab_orders: LabOrderSummary[]; prescriptions: PrescriptionSummary[] };
export type Appointment = { id: string; patient_id: string; facility_id: string; department_id: string; provider_id: string | null; appointment_at: string; reason: string | null; status: string };
export type Queue = { id: string; facility_id: string; department_id: string; name: string; status: string };
export type QueueEntry = { id: string; queue_id: string; patient_id: string; appointment_id: string | null; encounter_id: string | null; priority: string; status: string; queued_at: string; called_at: string | null; completed_at: string | null };
export type ApiErrorBody = { detail?: string | { code?: string; message?: string } };
