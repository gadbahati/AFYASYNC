import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AppointmentsPage } from "./pages/AppointmentsPage";
import { BenefitPackagesPage } from "./pages/BenefitPackagesPage";
import { BillingPage } from "./pages/BillingPage";
import { ClaimsPage } from "./pages/ClaimsPage";
import { CommandCentrePage } from "./pages/CommandCentrePage";
import { CoverageSimulatorPage } from "./pages/CoverageSimulatorPage";
import { DashboardPage } from "./pages/DashboardPage";
import { ShaLookupPage } from "./pages/ShaLookupPage";
import { LaboratoryWorkflowPage } from "./pages/LaboratoryWorkflowPage";
import { PharmacyPage } from "./pages/PharmacyPage";
import { EncounterDetailPage } from "./pages/EncounterDetailPage";
import { FacilitySelectPage } from "./pages/FacilitySelectPage";
import { LoginPage } from "./pages/LoginPage";
import { NationalCommandCentrePage } from "./pages/NationalCommandCentrePage";
import { NationalFacilitiesPage } from "./pages/NationalFacilitiesPage";
import { NationalPayerNetworkPage } from "./pages/NationalPayerNetworkPage";
import { NationalStaffPage } from "./pages/NationalStaffPage";
import { NewEncounterPage } from "./pages/NewEncounterPage";
import { NewPatientPage } from "./pages/NewPatientPage";
import { PatientDetailPage } from "./pages/PatientDetailPage";
import { PatientsPage } from "./pages/PatientsPage";
import { QueuePage } from "./pages/QueuePage";
import { ReferralsPage } from "./pages/ReferralsPage";

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
              <Route path="/command-centre" element={<CommandCentrePage />} />
              <Route path="/national-command-centre" element={<NationalCommandCentrePage />} />
              <Route path="/national-facilities" element={<NationalFacilitiesPage />} />
              <Route path="/national-staff" element={<NationalStaffPage />} />
              <Route path="/national-payers" element={<NationalPayerNetworkPage />} />
              <Route path="/coverage-simulator" element={<CoverageSimulatorPage />} />
              <Route path="/patients" element={<PatientsPage />} />
              <Route path="/patients/new" element={<NewPatientPage />} />
              <Route path="/patients/sha-lookup" element={<ShaLookupPage />} />
              <Route path="/patients/:patientId" element={<PatientDetailPage />} />
              <Route path="/patients/:patientId/encounters/new" element={<NewEncounterPage />} />
              <Route path="/encounters/:encounterId" element={<EncounterDetailPage />} />
              <Route path="/appointments" element={<AppointmentsPage />} />
              <Route path="/queue" element={<QueuePage />} />
              <Route path="/benefits" element={<BenefitPackagesPage />} />
              <Route path="/laboratory" element={<LaboratoryWorkflowPage />} />
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
