export type NationalCapacity = {
  active_facilities: number;
  active_departments: number;
  scheduled_appointments: number;
  waiting_queue_entries: number;
  total_beds: number;
  available_beds: number;
  occupied_beds: number;
  emergency_waiting: number;
  facilities: Array<{
    facility_id: string;
    facility_code: string;
    facility_name: string;
    county: string | null;
    departments: number;
    scheduled_appointments: number;
    waiting_queue_entries: number;
    total_beds: number;
    available_beds: number;
    occupied_beds: number;
    emergency_waiting: number;
  }>;
};
