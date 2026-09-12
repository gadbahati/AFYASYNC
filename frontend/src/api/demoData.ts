/** TEMPORARY offline demo data — remove with demo bypass before production go-live. */

import type {
  ClinicalTimeline,
  Department,
  Encounter,
  FacilityReport,
  Patient,
  PatientListResponse,
} from "./types";

export const DEMO_FACILITY_ID = "00000000-0000-4000-8000-0000000000f1";
export const DEMO_FACILITY_NAME = "AfyaSync National Pilot Facility";
export const DEMO_USERNAME = "demo.viewer";

const DEMO_PATIENTS: Patient[] = [
  {
    id: "00000000-0000-4000-8000-0000000000p1",
    afya_id: "AFYA-DEMO-001",
    first_name: "Amina",
    middle_name: null,
    last_name: "Wanjiku",
    date_of_birth: "1992-04-12",
    sex: "FEMALE",
    phone: "+254712000001",
    email: null,
    address: "Nairobi",
    status: "ACTIVE",
  },
  {
    id: "00000000-0000-4000-8000-0000000000p2",
    afya_id: "AFYA-DEMO-002",
    first_name: "Brian",
    middle_name: "Otieno",
    last_name: "Ochieng",
    date_of_birth: "1985-11-03",
    sex: "MALE",
    phone: "+254712000002",
    email: null,
    address: "Kisumu",
    status: "ACTIVE",
  },
  {
    id: "00000000-0000-4000-8000-0000000000p3",
    afya_id: "AFYA-DEMO-003",
    first_name: "Faith",
    middle_name: null,
    last_name: "Mwangi",
    date_of_birth: "2001-07-21",
    sex: "FEMALE",
    phone: "+254712000003",
    email: "faith.demo@example.com",
    address: "Nakuru",
    status: "ACTIVE",
  },
];

export function demoFacilityReport(): FacilityReport {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 30);
  return {
    facility_id: DEMO_FACILITY_ID,
    start_date: start.toISOString().slice(0, 10),
    end_date: end.toISOString().slice(0, 10),
    patients: 128,
    encounters: 94,
    charges_total: "485000",
    invoices_total: "462000",
    payer_billed: "310000",
    patient_billed: "152000",
    confirmed_payments: "298500",
    claims: 41,
    claims_amount: "310000",
    claims_approved: "276000",
    claims_paid: "241000",
  };
}

export function demoListPatients(limit = 50, offset = 0): PatientListResponse {
  const items = DEMO_PATIENTS.slice(offset, offset + limit);
  return { items, total: DEMO_PATIENTS.length, limit, offset };
}

export function demoGetPatient(id: string): Patient {
  const found = DEMO_PATIENTS.find((p) => p.id === id);
  if (!found) throw new Error("PATIENT_NOT_FOUND");
  return found;
}

export function demoCreatePatient(payload: {
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  date_of_birth?: string | null;
  sex?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
}): Patient {
  const patient: Patient = {
    id: crypto.randomUUID(),
    afya_id: `AFYA-DEMO-${String(DEMO_PATIENTS.length + 1).padStart(3, "0")}`,
    first_name: payload.first_name,
    middle_name: payload.middle_name ?? null,
    last_name: payload.last_name,
    date_of_birth: payload.date_of_birth ?? null,
    sex: payload.sex ?? null,
    phone: payload.phone ?? null,
    email: payload.email ?? null,
    address: payload.address ?? null,
    status: "ACTIVE",
  };
  DEMO_PATIENTS.unshift(patient);
  return patient;
}

export function demoDepartments(): Department[] {
  return [
    {
      id: "00000000-0000-4000-8000-0000000000d1",
      facility_id: DEMO_FACILITY_ID,
      name: "Outpatient",
      code: "OPD",
      status: "ACTIVE",
    },
    {
      id: "00000000-0000-4000-8000-0000000000d2",
      facility_id: DEMO_FACILITY_ID,
      name: "Emergency",
      code: "A&E",
      status: "ACTIVE",
    },
  ];
}

export function demoCreateEncounter(payload: {
  patient_id: string;
  facility_id: string;
  department_id: string;
  encounter_type: string;
  reason?: string | null;
}): Encounter {
  return {
    id: crypto.randomUUID(),
    encounter_id: `ENC-DEMO-${Date.now()}`,
    patient_id: payload.patient_id,
    facility_id: payload.facility_id,
    department_id: payload.department_id,
    encounter_type: payload.encounter_type,
    reason: payload.reason ?? null,
    status: "OPEN",
    started_at: new Date().toISOString(),
    ended_at: null,
    created_by: "00000000-0000-4000-8000-0000000000u1",
  };
}

export function demoClinicalTimeline(encounterId: string): ClinicalTimeline {
  const encounter = demoCreateEncounter({
    patient_id: DEMO_PATIENTS[0].id,
    facility_id: DEMO_FACILITY_ID,
    department_id: demoDepartments()[0].id,
    encounter_type: "OUTPATIENT",
    reason: "Demo walkthrough",
  });
  encounter.id = encounterId;
  return {
    encounter,
    vitals: [],
    consultation: null,
    diagnoses: [],
    lab_orders: [],
    prescriptions: [],
  };
}
