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
import { IntegrationOperationsPage } from "./pages/IntegrationOperationsPage";
import { ShaLookupPage } from "./pages/ShaLookupPage";
import { SHAEligibilityPage } from "./pages/SHAEligibilityPage";
import { LaboratoryWorkflowPage } from "./pages/LaboratoryWorkflowPage";
import { PharmacyPage } from "./pages/PharmacyPage";
import { EncounterDetailPage } from "./pages/EncounterDetailPage";
import { EncountersPage } from "./pages/EncountersPage";
import { EntryPage } from "./pages/EntryPage";
import { FacilitySelectPage } from "./pages/FacilitySelectPage";
import { LoginPage } from "./pages/LoginPage";
import { MCHPage } from "./pages/MCHPage";
import { NationalBenefitConfigurationPage } from "./pages/NationalBenefitConfigurationPage";
import { NationalCommandCentrePage } from "./pages/NationalCommandCentrePage";
import { NationalFacilitiesPage } from "./pages/NationalFacilitiesPage";
import { NationalIdentityPage } from "./pages/NationalIdentityPage";
import { NationalIntelligencePage } from "./pages/NationalIntelligencePage";
import { NationalPayerNetworkPage } from "./pages/NationalPayerNetworkPage";
import { NationalStaffPage } from "./pages/NationalStaffPage";
import { NationalSupplyPage } from "./pages/NationalSupplyPage";
import { NationalSupplyPlanningPage } from "./pages/NationalSupplyPlanningPage";
import { NationalReferralsPage } from "./pages/NationalReferralsPage";
import { NationalCapacityPage } from "./pages/NationalCapacityPage";
import { NewEncounterPage } from "./pages/NewEncounterPage";
import { NewPatientPage } from "./pages/NewPatientPage";
import { PatientBookAppointmentPage } from "./pages/PatientBookAppointmentPage";
import { PatientConsentsPage } from "./pages/PatientConsentsPage";
import { PatientCoveragePage } from "./pages/PatientCoveragePage";
import { PatientDetailPage } from "./pages/PatientDetailPage";
import { PatientJourneyPage } from "./pages/PatientJourneyPage";
import { PatientLoginPage } from "./pages/PatientLoginPage";
import { PatientMessagesPage } from "./pages/PatientMessagesPage";
import { PatientPortalHomePage } from "./pages/PatientPortalHomePage";
import { PatientRegisterPage } from "./pages/PatientRegisterPage";
import { PatientResetPage } from "./pages/PatientResetPage";
import { PatientVisitsPage } from "./pages/PatientVisitsPage";
import { PatientsPage } from "./pages/PatientsPage";
import { CarePlansPage } from "./pages/CarePlansPage";
import { PatientSafetyPage } from "./pages/PatientSafetyPage";
import { QueuePage } from "./pages/QueuePage";
import { ReferralsPage } from "./pages/ReferralsPage";
import { InteroperabilityPage } from "./pages/InteroperabilityPage";
import { InteroperabilityClinicalPage } from "./pages/InteroperabilityClinicalPage";
import { ReportsPage } from "./pages/ReportsPage";

export default function App() {
  return <AuthProvider><BrowserRouter><Routes>
    <Route path="/login" element={<EntryPage />} />
    <Route path="/login/facility" element={<LoginPage />} />
    <Route path="/login/patient" element={<PatientLoginPage />} />
    <Route path="/login/patient/register" element={<PatientRegisterPage />} />
    <Route path="/login/patient/reset" element={<PatientResetPage />} />
    <Route path="/select-facility" element={<FacilitySelectPage />} />
    <Route path="/portal" element={<PatientPortalHomePage />} />
    <Route path="/portal/book" element={<PatientBookAppointmentPage />} />
    <Route path="/portal/messages" element={<PatientMessagesPage />} />
    <Route path="/portal/encounters" element={<PatientVisitsPage />} />
    <Route path="/portal/consents" element={<PatientConsentsPage />} />
    <Route path="/portal/coverage" element={<PatientCoveragePage />} />
    <Route element={<ProtectedRoute />}><Route element={<Layout />}>
      <Route path="/" element={<DashboardPage />} /><Route path="/command-centre" element={<CommandCentrePage />} /><Route path="/national-command-centre" element={<NationalCommandCentrePage />} /><Route path="/national-intelligence" element={<NationalIntelligencePage />} /><Route path="/national-identity" element={<NationalIdentityPage />} /><Route path="/national-facilities" element={<NationalFacilitiesPage />} /><Route path="/national-staff" element={<NationalStaffPage />} /><Route path="/national-payers" element={<NationalPayerNetworkPage />} /><Route path="/national-benefits" element={<NationalBenefitConfigurationPage />} /><Route path="/national-supply" element={<NationalSupplyPage />} /><Route path="/national/supply/planning" element={<NationalSupplyPlanningPage />} /><Route path="/national/referrals" element={<NationalReferralsPage />} /><Route path="/national/capacity" element={<NationalCapacityPage />} /><Route path="/coverage-simulator" element={<CoverageSimulatorPage />} />
      <Route path="/coverage/sha-eligibility" element={<SHAEligibilityPage />} /><Route path="/integrations" element={<IntegrationOperationsPage />} /><Route path="/interoperability" element={<InteroperabilityPage />} /><Route path="/interoperability/clinical" element={<InteroperabilityClinicalPage />} /><Route path="/patients" element={<PatientsPage />} /><Route path="/patients/new" element={<NewPatientPage />} /><Route path="/patients/sha-lookup" element={<ShaLookupPage />} /><Route path="/patients/:patientId/journey" element={<PatientJourneyPage />} /><Route path="/patients/:patientId/care-plans" element={<CarePlansPage />} /><Route path="/patients/:patientId/safety" element={<PatientSafetyPage />} /><Route path="/patients/:patientId" element={<PatientDetailPage />} /><Route path="/patients/:patientId/encounters/new" element={<NewEncounterPage />} /><Route path="/encounters" element={<EncountersPage />} /><Route path="/encounters/:encounterId" element={<EncounterDetailPage />} /><Route path="/appointments" element={<AppointmentsPage />} /><Route path="/queue" element={<QueuePage />} /><Route path="/mch" element={<MCHPage />} /><Route path="/benefits" element={<BenefitPackagesPage />} /><Route path="/laboratory" element={<LaboratoryWorkflowPage />} /><Route path="/pharmacy" element={<PharmacyPage />} /><Route path="/billing" element={<BillingPage />} /><Route path="/claims" element={<ClaimsPage />} /><Route path="/referrals" element={<ReferralsPage />} /><Route path="/reports" element={<ReportsPage />} />
    </Route></Route><Route path="*" element={<Navigate to="/login" replace />} />
  </Routes></BrowserRouter></AuthProvider>;
}
