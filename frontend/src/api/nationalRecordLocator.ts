export type NationalRecordFacility = {
  facility_id: string;
  facility_code: string;
  facility_name: string;
  county: string | null;
  enrollment_status: string;
};

export type NationalRecordLocatorResponse = {
  afya_id: string;
  person_id: string;
  record_status: string;
  facilities: NationalRecordFacility[];
};
