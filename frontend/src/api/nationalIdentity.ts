export type NationalIdentityResolution = {
  afya_id: string;
  person_id: string;
  first_name: string;
  middle_name: string | null;
  last_name: string;
  date_of_birth: string | null;
  sex: string | null;
  patient_status: string;
  active_facility_count: number;
  identity_status: string;
};
