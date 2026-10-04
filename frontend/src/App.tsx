import { createElement } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { WorkspaceProvider } from "./workspaces/WorkspaceContext";
import { GlobalCommand } from "./components/GlobalCommand";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { GovernmentProtectedRoute } from "./components/GovernmentProtectedRoute";
import { EntryPage } from "./pages/EntryPage";
import { LoginPage } from "./pages/LoginPage";
import { PatientLoginPage } from "./pages/PatientLoginPage";
import { GovernmentLoginPage } from "./pages/GovernmentLoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EncountersPage } from "./pages/EncountersPage";
import { ClinicalWorklistPage } from "./pages/ClinicalWorklistPage";
import { EncounterDetailPage } from "./pages/EncounterDetailPage";
import { PatientsPage } from "./pages/PatientsPage";
import { PatientDetailPage } from "./pages/PatientDetailPage";
import { NewEncounterPage } from "./pages/NewEncounterPage";
import WorkspaceHomePage from "./pages/WorkspaceHomePage";
import { LaboratoryWorkflowPage } from "./pages/LaboratoryWorkflowPage";
import { PharmacyPage } from "./pages/PharmacyPage";
import { RadiologyPage } from "./pages/RadiologyPage";
import { ClaimsPage } from "./pages/ClaimsPage";
import { BillingPage } from "./pages/BillingPage";
import { AppointmentsPage } from "./pages/AppointmentsPage";
import { MCHPage } from "./pages/MCHPage";
import { FacilityMessagesPage } from "./pages/FacilityMessagesPage";
import { ReferralsPage } from "./pages/ReferralsPage";
import { PatientPortalHomePage } from "./pages/PatientPortalHomePage";
import { PatientVisitsPage } from "./pages/PatientVisitsPage";
import { PatientBookAppointmentPage } from "./pages/PatientBookAppointmentPage";
import { PatientMessagesPage } from "./pages/PatientMessagesPage";
import { PatientConsentsPage } from "./pages/PatientConsentsPage";
import { PatientCoveragePage } from "./pages/PatientCoveragePage";
import { PatientContinuityCardPage } from "./pages/PatientContinuityCardPage";
import { PatientResultsPage } from "./pages/PatientResultsPage";
import { QueuePage } from "./pages/QueuePage";
import { NewPatientPage } from "./pages/NewPatientPage";
import { HouseholdWalletPage } from "./pages/HouseholdWalletPage";
import { CareCoordinationPage } from "./pages/CareCoordinationPage";
import { InteroperabilityPage } from "./pages/InteroperabilityPage";
import { InteroperabilityClinicalPage } from "./pages/InteroperabilityClinicalPage";
import { HealthExchangePage } from "./pages/HealthExchangePage";
import { UniversalIdentityPage } from "./pages/UniversalIdentityPage";
import { NationalIdentityPage } from "./pages/NationalIdentityPage";
import { ReferralRoutingPage } from "./pages/ReferralRoutingPage";
import { ReferralBookingPage } from "./pages/ReferralBookingPage";
import { ClaimsClearinghousePage } from "./pages/ClaimsClearinghousePage";
import { SHAEligibilityPage } from "./pages/SHAEligibilityPage";
import FinancialCommandCentrePage from "./pages/FinancialCommandCentrePage";
import PayerCommandPage from "./pages/PayerCommandPage";
import RevenueControlTowerPage from "./pages/RevenueControlTowerPage";
import RevenueCashAssurancePage from "./pages/RevenueCashAssurancePage";
import CollectionWorkQueuePage from "./pages/CollectionWorkQueuePage";
import RevenueRecoveryPage from "./pages/RevenueRecoveryPage";
import DenialAppealsPage from "./pages/DenialAppealsPage";
import ContractGuardrailsPage from "./pages/ContractGuardrailsPage";
import ContractExecutionPage from "./pages/ContractExecutionPage";
import { NationalCommandCentrePage } from "./pages/NationalCommandCentrePage";
import { NationalIntelligencePage } from "./pages/NationalIntelligencePage";
import { NationalFacilitiesPage } from "./pages/NationalFacilitiesPage";
import { NationalReferralsPage } from "./pages/NationalReferralsPage";
import { NationalCapacityPage } from "./pages/NationalCapacityPage";
import { NationalSupplyPage } from "./pages/NationalSupplyPage";
import { NationalSupplyPlanningPage } from "./pages/NationalSupplyPlanningPage";
import { SecurityOperationsPage } from "./pages/SecurityOperationsPage";
import TenancyPage from "./pages/TenancyPage";
import { CertificationPage } from "./pages/CertificationPage";
import { RetentionPage } from "./pages/RetentionPage";
import { RiskRegisterPage } from "./pages/RiskRegisterPage";
import { ChangeControlPage } from "./pages/ChangeControlPage";
import { NationalReadinessPage } from "./pages/NationalReadinessPage";
import { ProductionPage } from "./pages/ProductionPage";
import BusinessContinuityPage from "./pages/BusinessContinuityPage";
import { OfflineClinicPage } from "./pages/OfflineClinicPage";
import { FacilityContinuityScanPage } from "./pages/FacilityContinuityScanPage";
import { DisasterRecoveryPage } from "./pages/DisasterRecoveryPage";
import { ObservabilityPage } from "./pages/ObservabilityPage";
import { PerformancePage } from "./pages/PerformancePage";
import { IntegrationOperationsPage } from "./pages/IntegrationOperationsPage";
import ProductReadinessPage from "./pages/ProductReadinessPage";
import { CommandCentrePage } from "./pages/CommandCentrePage";
import { WarehousePage } from "./pages/WarehousePage";
import { ExecutiveRevenuePage } from "./pages/ExecutiveRevenuePage";
import { RevenueActionPrioritiesPage } from "./pages/RevenueActionPrioritiesPage";
import { RecoveryCashConversionPage } from "./pages/RecoveryCashConversionPage";
import { CoverageSimulatorPage } from "./pages/CoverageSimulatorPage";
import { GovernmentPortalHomePage } from "./pages/GovernmentPortalHomePage";
import { GovernmentModulePage } from "./pages/GovernmentModulePage";

/** Phase 149+ — facility routes and workspace architecture. */
export default function App() {
  const facilityShell = (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/workspace" element={<WorkspaceHomePage />} />
        <Route path="/patients" element={<PatientsPage />} />
        <Route path="/patients/:patientId" element={<PatientDetailPage />} />
        <Route path="/patients/:patientId/encounters/new" element={<NewEncounterPage />} />
        <Route path="/clinical-worklist" element={<ClinicalWorklistPage />} />
        <Route path="/laboratory" element={<LaboratoryWorkflowPage />} />
        <Route path="/pharmacy" element={<PharmacyPage />} />
        <Route path="/radiology" element={<RadiologyPage />} />
        <Route path="/encounters" element={<EncountersPage />} />
        <Route path="/encounters/:encounterId" element={<EncounterDetailPage />} />
        <Route path="/appointments" element={<AppointmentsPage />} />
        <Route path="/mch" element={<MCHPage />} />
        <Route path="/billing" element={<BillingPage />} />
        <Route path="/claims" element={<ClaimsPage />} />
        <Route path="/messages" element={<FacilityMessagesPage />} />
        <Route path="/referrals" element={<ReferralsPage />} />
        <Route path="/queue" element={<QueuePage />} />
        <Route path="/patients/new" element={<NewPatientPage />} />
        <Route path="/household-wallet" element={<HouseholdWalletPage />} />
        <Route path="/care-coordination" element={<CareCoordinationPage />} />
        <Route path="/interoperability" element={<InteroperabilityPage />} />
        <Route path="/interoperability/clinical" element={<InteroperabilityClinicalPage />} />
        <Route path="/health-exchange" element={<HealthExchangePage />} />
        <Route path="/universal-identity" element={<UniversalIdentityPage />} />
        <Route path="/national-identity" element={<NationalIdentityPage />} />
        <Route path="/referral-routing" element={<ReferralRoutingPage />} />
        <Route path="/referral-booking" element={<ReferralBookingPage />} />
        <Route path="/claims-clearinghouse" element={<ClaimsClearinghousePage />} />
        <Route path="/coverage/sha-eligibility" element={<SHAEligibilityPage />} />
        <Route path="/financial-command-centre" element={<FinancialCommandCentrePage />} />
        <Route path="/payer-command" element={<PayerCommandPage />} />
        <Route path="/revenue-control-tower" element={<RevenueControlTowerPage />} />
        <Route path="/revenue-cash-assurance" element={<RevenueCashAssurancePage />} />
        <Route path="/collection-work" element={<CollectionWorkQueuePage />} />
        <Route path="/revenue-recovery" element={<RevenueRecoveryPage />} />
        <Route path="/denial-appeals" element={<DenialAppealsPage />} />
        <Route path="/contract-guardrails" element={<ContractGuardrailsPage />} />
        <Route path="/contract-execution" element={<ContractExecutionPage />} />
        <Route path="/national-command-centre" element={<NationalCommandCentrePage />} />
        <Route path="/national-intelligence" element={<NationalIntelligencePage />} />
        <Route path="/national-facilities" element={<NationalFacilitiesPage />} />
        <Route path="/national/referrals" element={<NationalReferralsPage />} />
        <Route path="/national/capacity" element={<NationalCapacityPage />} />
        <Route path="/national-supply" element={<NationalSupplyPage />} />
        <Route path="/national/supply/planning" element={<NationalSupplyPlanningPage />} />
        <Route path="/security-operations" element={<SecurityOperationsPage />} />
        <Route path="/tenancy" element={<TenancyPage />} />
        <Route path="/certification" element={<CertificationPage />} />
        <Route path="/retention" element={<RetentionPage />} />
        <Route path="/risk-register" element={<RiskRegisterPage />} />
        <Route path="/change-control" element={<ChangeControlPage />} />
        <Route path="/national-readiness" element={<NationalReadinessPage />} />
        <Route path="/production" element={<ProductionPage />} />
        <Route path="/business-continuity" element={<BusinessContinuityPage />} />
        <Route path="/offline-clinic" element={<OfflineClinicPage />} />
        <Route path="/continuity-scan" element={<FacilityContinuityScanPage />} />
        <Route path="/disaster-recovery" element={<DisasterRecoveryPage />} />
        <Route path="/observability" element={<ObservabilityPage />} />
        <Route path="/performance" element={<PerformancePage />} />
        <Route path="/integrations" element={<IntegrationOperationsPage />} />
        <Route path="/product-readiness" element={<ProductReadinessPage />} />
        <Route path="/command-centre" element={<CommandCentrePage />} />
        <Route path="/warehouse" element={<WarehousePage />} />
        <Route path="/executive-revenue" element={<ExecutiveRevenuePage />} />
        <Route path="/revenue-action-priorities" element={<RevenueActionPrioritiesPage />} />
        <Route path="/recovery-cash-conversion" element={<RecoveryCashConversionPage />} />
        <Route path="/coverage-simulator" element={<CoverageSimulatorPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );

  return (
    <AuthProvider>
      <BrowserRouter>
        <WorkspaceProvider>
          <GlobalCommand />
          <Routes>
            <Route path="/" element={<EntryPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/login/patient" element={<PatientLoginPage />} />
            <Route path="/login/facility" element={<LoginPage />} />
            <Route path="/login/government" element={<GovernmentLoginPage />} />
            <Route path="/portal" element={<PatientPortalHomePage />} />
            <Route path="/portal/results" element={<PatientResultsPage />} />
            <Route path="/portal/encounters" element={<PatientVisitsPage />} />
            <Route path="/portal/book" element={<PatientBookAppointmentPage />} />
            <Route path="/portal/messages" element={<PatientMessagesPage />} />
            <Route path="/portal/consents" element={<PatientConsentsPage />} />
            <Route path="/portal/coverage" element={<PatientCoveragePage />} />
            <Route path="/portal/continuity-card" element={<PatientContinuityCardPage />} />
            <Route
              path="/*"
              element={createElement(ProtectedRoute, null, facilityShell)}
            />
            <Route
              path="/government/*"
              element={createElement(
                GovernmentProtectedRoute,
                null,
                <Layout>
                  <Routes>
                    <Route path="/" element={<GovernmentPortalHomePage />} />
                    <Route path="/facilities" element={<GovernmentModulePage />} />
                    <Route path="/analytics" element={<GovernmentModulePage />} />
                    <Route path="/reporting" element={<GovernmentModulePage />} />
                    <Route path="/interoperability" element={<GovernmentModulePage />} />
                    <Route path="/public-health" element={<GovernmentModulePage />} />
                    <Route path="/compliance" element={<GovernmentModulePage />} />
                    <Route path="*" element={<Navigate to="/government" replace />} />
                  </Routes>
                </Layout>,
              )}
            />
          </Routes>
        </WorkspaceProvider>
      </BrowserRouter>
    </AuthProvider>
  );
}
