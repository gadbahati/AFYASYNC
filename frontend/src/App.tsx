import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { DashboardPage } from "./pages/DashboardPage";
import {
  AppointmentsPage,
  BillingPage,
  ClaimsPage,
  LabPage,
  PharmacyPage,
  QueuePage,
  ReferralsPage,
} from "./pages/demoPages";
import { EncounterDetailPage } from "./pages/EncounterDetailPage";
import { FacilitySelectPage } from "./pages/FacilitySelectPage";
import { LoginPage } from "./pages/LoginPage";
import { NewEncounterPage } from "./pages/NewEncounterPage";
import { NewPatientPage } from "./pages/NewPatientPage";
import { PatientDetailPage } from "./pages/PatientDetailPage";
import { PatientsPage } from "./pages/PatientsPage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/select-facility" element={<FacilitySelectPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/patients" element={<PatientsPage />} />
              <Route path="/patients/new" element={<NewPatientPage />} />
              <Route path="/patients/:patientId" element={<PatientDetailPage />} />
              <Route path="/patients/:patientId/encounters/new" element={<NewEncounterPage />} />
              <Route path="/encounters/:encounterId" element={<EncounterDetailPage />} />
              <Route path="/appointments" element={<AppointmentsPage />} />
              <Route path="/queue" element={<QueuePage />} />
              <Route path="/laboratory" element={<LabPage />} />
              <Route path="/pharmacy" element={<PharmacyPage />} />
              <Route path="/billing" element={<BillingPage />} />
              <Route path="/claims" element={<ClaimsPage />} />
              <Route path="/referrals" element={<ReferralsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
