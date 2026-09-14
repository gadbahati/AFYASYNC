export type NationalCapacity = {
  active_facilities: number;
  active_departments: number;
  scheduled_appointments: number;
  waiting_queue_entries: number;
  facilities: Array<{
    facility_id: string;
    facility_code: string;
    facility_name: string;
    county: string | null;
    departments: number;
    scheduled_appointments: number;
    waiting_queue_entries: number;
  }>;
};
