import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { WorkspaceProvider } from "./workspaces/WorkspaceContext";
import { GlobalCommand } from "./components/GlobalCommand";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { ModuleAccessProvider } from "./auth/ModuleAccessContext";
import { ModuleGuard } from "./components/ModuleGuard";
import { AppointmentsPage } from "./pages/AppointmentsPage";
import { BenefitPackagesPage } from "./pages/BenefitPackagesPage";
import { BillingPage } from "./pages/BillingPage";
import { ClaimsPage } from "./pages/ClaimsPage";
import { CommandCentrePage } from "./pages/CommandCentrePage";
import { CoverageSimulatorPage } from "./pages/CoverageSimulatorPage";
import { DashboardPage } from "./pages/DashboardPage";
import { FacilityMessagesPage } from "./pages/FacilityMessagesPage";
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
import { AfyaCitizenPage } from "./pages/AfyaCitizenPage";
import { CitizenWalletPage } from "./pages/CitizenWalletPage";
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
import { TreatAbroadPage } from "./pages/TreatAbroadPage";
import { PatientContinuityCardPage } from "./pages/PatientContinuityCardPage";
import { ContinuityVerifyPage } from "./pages/ContinuityVerifyPage";
import { FacilityContinuityScanPage } from "./pages/FacilityContinuityScanPage";
import { OfflineClinicPage } from "./pages/OfflineClinicPage";
import { HouseholdWalletPage } from "./pages/HouseholdWalletPage";
import { SecurityOperationsPage } from "./pages/SecurityOperationsPage";
import { WorkforcePage } from "./pages/WorkforcePage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { TrainingPage } from "./pages/TrainingPage";
import { RolloutPage } from "./pages/RolloutPage";
import { WarehousePage } from "./pages/WarehousePage";
import { CertificationPage } from "./pages/CertificationPage";
import { ProductionPage } from "./pages/ProductionPage";
import { ObservabilityPage } from "./pages/ObservabilityPage";
import { RetentionPage } from "./pages/RetentionPage";
import { PartnerSandboxPage } from "./pages/PartnerSandboxPage";
import { DisasterRecoveryPage } from "./pages/DisasterRecoveryPage";
import { ChangeControlPage } from "./pages/ChangeControlPage";
import { PilotHandoverPage } from "./pages/PilotHandoverPage";
import { PerformancePage } from "./pages/PerformancePage";
import { RiskRegisterPage } from "./pages/RiskRegisterPage";
import { NationalReadinessPage } from "./pages/NationalReadinessPage";
import { NationalFinancingExchangePage } from "./pages/NationalFinancingExchangePage";
import { EligibilityEnginePage } from "./pages/EligibilityEnginePage";
import { UniversalIdentityPage } from "./pages/UniversalIdentityPage";
import { FinancingPreauthorizationPage } from "./pages/FinancingPreauthorizationPage";
import { AdjudicationPage } from "./pages/AdjudicationPage";
import SettlementPage from "./pages/SettlementPage";
import FraudIntegrityPage from "./pages/FraudIntegrityPage";
import { FinancingWalletPage } from "./pages/FinancingWalletPage";
import { ProviderNetworkPage } from "./pages/ProviderNetworkPage";
import { HealthExchangePage } from "./pages/HealthExchangePage";
import { CareCoordinationPage } from "./pages/CareCoordinationPage";
import { ReferralRoutingPage } from "./pages/ReferralRoutingPage";
import { ReferralBookingPage } from "./pages/ReferralBookingPage";
import { BenefitEnginePage } from "./pages/BenefitEnginePage";
import { ClaimsClearinghousePage } from "./pages/ClaimsClearinghousePage";
import RevenueRecoveryPage from "./pages/RevenueRecoveryPage";
import RevenueAnomalyPage from "./pages/RevenueAnomalyPage";
import FinancialCommandCentrePage from "./pages/FinancialCommandCentrePage";
import CollectionWorkQueuePage from "./pages/CollectionWorkQueuePage";
import RevenueResolutionPage from "./pages/RevenueResolutionPage";
import DenialAppealsPage from "./pages/DenialAppealsPage";
import PayerCommandPage from "./pages/PayerCommandPage";
import TariffIntelligencePage from "./pages/TariffIntelligencePage";
import ContractRenewalPage from "./pages/ContractRenewalPage";
import PayerNegotiationPage from "./pages/PayerNegotiationPage";
import ContractExecutionPage from "./pages/ContractExecutionPage";
import ContractActivationPage from "./pages/ContractActivationPage";
import ContractGuardrailsPage from "./pages/ContractGuardrailsPage";
import ContractCashCommandPage from "./pages/ContractCashCommandPage";
import PayerContractCashPage from "./pages/PayerContractCashPage";
import LeakageIntelligencePage from "./pages/LeakageIntelligencePage";
import RecoveryCashConversionPage from "./pages/RecoveryCashConversionPage";
import ExecutiveRevenuePage from "./pages/ExecutiveRevenuePage";
import RevenueControlTowerPage from "./pages/RevenueControlTowerPage";
import RevenueActionPrioritiesPage from "./pages/RevenueActionPrioritiesPage";
import RevenueWorkflowAutomationPage from "./pages/RevenueWorkflowAutomationPage";
import CashClosureCommandPage from "./pages/CashClosureCommandPage";
import RevenueCashAssurancePage from "./pages/RevenueCashAssurancePage";
import WorkspaceHomePage from "./pages/WorkspaceHomePage";
import TenancyPage from "./pages/TenancyPage";
import ProductReadinessPage from "./pages/ProductReadinessPage";
import BusinessContinuityPage from "./pages/BusinessContinuityPage";

export default function App() {
  return <AuthProvider><WorkspaceProvider><BrowserRouter><GlobalCommand /><Routes>
    <Route path="/login" element={<EntryPage />} />
    <Route path="/login/facility" element={<LoginPage />} />
    <Route path="/login/patient" element={<PatientLoginPage />} />
    <Route path="/login/patient/register" element={<PatientRegisterPage />} />
    <Route path="/login/patient/reset" element={<PatientResetPage />} />
    <Route path="/select-facility" element={<FacilitySelectPage />} />
    <Route path="/portal" element={<PatientPortalHomePage />} />
    <Route path="/portal/citizen" element={<AfyaCitizenPage />} />
    <Route path="/portal/wallet" element={<CitizenWalletPage />} />
    <Route path="/portal/book" element={<PatientBookAppointmentPage />} />
    <Route path="/portal/messages" element={<PatientMessagesPage />} />
    <Route path="/portal/encounters" element={<PatientVisitsPage />} />
    <Route path="/portal/consents" element={<PatientConsentsPage />} />
    <Route path="/portal/coverage" element={<PatientCoveragePage />} />
    <Route path="/portal/continuity-card" element={<PatientContinuityCardPage />} />
    <Route path="/continuity/:token" element={<ContinuityVerifyPage />} />
    <Route path="/continuity" element={<ContinuityVerifyPage />} />
    <Route element={<ProtectedRoute />}>
      <Route element={<ModuleAccessProvider><ModuleGuard /></ModuleAccessProvider>}>
        <Route element={<Layout />}>
      <Route path="/" element={<DashboardPage />} /><Route path="/workspace" element={<WorkspaceHomePage />} /><Route path="/tenancy" element={<TenancyPage />} /><Route path="/product-readiness" element={<ProductReadinessPage />} /><Route path="/business-continuity" element={<BusinessContinuityPage />} /><Route path="/command-centre" element={<CommandCentrePage />} /><Route path="/national-command-centre" element={<NationalCommandCentrePage />} /><Route path="/national-intelligence" element={<NationalIntelligencePage />} /><Route path="/national-identity" element={<NationalIdentityPage />} /><Route path="/national-facilities" element={<NationalFacilitiesPage />} /><Route path="/national-staff" element={<NationalStaffPage />} /><Route path="/national-payers" element={<NationalPayerNetworkPage />} /><Route path="/national-benefits" element={<NationalBenefitConfigurationPage />} /><Route path="/national-supply" element={<NationalSupplyPage />} /><Route path="/national/supply/planning" element={<NationalSupplyPlanningPage />} /><Route path="/national/referrals" element={<NationalReferralsPage />} /><Route path="/national/capacity" element={<NationalCapacityPage />} /><Route path="/coverage-simulator" element={<CoverageSimulatorPage />} />
      <Route path="/coverage/sha-eligibility" element={<SHAEligibilityPage />} /><Route path="/integrations" element={<IntegrationOperationsPage />} /><Route path="/interoperability" element={<InteroperabilityPage />} /><Route path="/interoperability/clinical" element={<InteroperabilityClinicalPage />} /><Route path="/patients" element={<PatientsPage />} /><Route path="/patients/new" element={<NewPatientPage />} /><Route path="/patients/sha-lookup" element={<ShaLookupPage />} /><Route path="/continuity-scan" element={<FacilityContinuityScanPage />} /><Route path="/offline-clinic" element={<OfflineClinicPage />} /><Route path="/household-wallet" element={<HouseholdWalletPage />} /><Route path="/security-operations" element={<SecurityOperationsPage />} /><Route path="/workforce" element={<WorkforcePage />} /><Route path="/onboarding" element={<OnboardingPage />} /><Route path="/training" element={<TrainingPage />} /><Route path="/rollout" element={<RolloutPage />} /><Route path="/warehouse" element={<WarehousePage />} /><Route path="/certification" element={<CertificationPage />} /><Route path="/production" element={<ProductionPage />} /><Route path="/observability" element={<ObservabilityPage />} /><Route path="/retention" element={<RetentionPage />} /><Route path="/partner-sandbox" element={<PartnerSandboxPage />} /><Route path="/disaster-recovery" element={<DisasterRecoveryPage />} /><Route path="/change-control" element={<ChangeControlPage />} /><Route path="/pilot-handover" element={<PilotHandoverPage />} /><Route path="/performance" element={<PerformancePage />} /><Route path="/risk-register" element={<RiskRegisterPage />} /><Route path="/national-readiness" element={<NationalReadinessPage />} /><Route path="/national-financing" element={<NationalFinancingExchangePage />} /><Route path="/eligibility" element={<EligibilityEnginePage />} /><Route path="/universal-identity" element={<UniversalIdentityPage />} /><Route path="/financing-preauthorization" element={<FinancingPreauthorizationPage />} /><Route path="/adjudication" element={<AdjudicationPage />} />
        <Route path="/settlements" element={<SettlementPage />} />
        <Route path="/fraud-integrity" element={<FraudIntegrityPage />} /><Route path="/financing-wallet" element={<FinancingWalletPage />} /><Route path="/provider-network" element={<ProviderNetworkPage />} /><Route path="/health-exchange" element={<HealthExchangePage />} /><Route path="/care-coordination" element={<CareCoordinationPage />} /><Route path="/referral-routing" element={<ReferralRoutingPage />} /><Route path="/referral-booking" element={<ReferralBookingPage />} /><Route path="/benefit-engine" element={<BenefitEnginePage />} /><Route path="/claims-clearinghouse" element={<ClaimsClearinghousePage />} /><Route path="/revenue-recovery" element={<RevenueRecoveryPage />} /><Route path="/revenue-anomalies" element={<RevenueAnomalyPage />} /><Route path="/financial-command-centre" element={<FinancialCommandCentrePage />} />
        <Route path="/collection-work" element={<CollectionWorkQueuePage />} /><Route path="/revenue-resolution" element={<RevenueResolutionPage />} /><Route path="/denial-appeals" element={<DenialAppealsPage />} /><Route path="/payer-command" element={<PayerCommandPage />} /><Route path="/tariff-intelligence" element={<TariffIntelligencePage />} /><Route path="/contract-renewal" element={<ContractRenewalPage />} /><Route path="/payer-negotiation" element={<PayerNegotiationPage />} /><Route path="/contract-execution" element={<ContractExecutionPage />} /><Route path="/contract-activation" element={<ContractActivationPage />} /><Route path="/contract-guardrails" element={<ContractGuardrailsPage />} /><Route path="/contract-cash-command" element={<ContractCashCommandPage />} /><Route path="/payer-contract-cash" element={<PayerContractCashPage />} /><Route path="/leakage-intelligence" element={<LeakageIntelligencePage />} /><Route path="/recovery-cash-conversion" element={<RecoveryCashConversionPage />} /><Route path="/executive-revenue" element={<ExecutiveRevenuePage />} /><Route path="/revenue-control-tower" element={<RevenueControlTowerPage />} /><Route path="/revenue-action-priorities" element={<RevenueActionPrioritiesPage />} /><Route path="/revenue-workflow-automation" element={<RevenueWorkflowAutomationPage />} /><Route path="/cash-closure-command" element={<CashClosureCommandPage />} /><Route path="/revenue-cash-assurance" element={<RevenueCashAssurancePage />} /><Route path="/patients/:patientId/journey" element={<PatientJourneyPage />} /><Route path="/patients/:patientId/care-plans" element={<CarePlansPage />} /><Route path="/patients/:patientId/safety" element={<PatientSafetyPage />} /><Route path="/patients/:patientId" element={<PatientDetailPage />} /><Route path="/patients/:patientId/encounters/new" element={<NewEncounterPage />} /><Route path="/encounters" element={<EncountersPage />} /><Route path="/encounters/:encounterId" element={<EncounterDetailPage />} /><Route path="/appointments" element={<AppointmentsPage />} /><Route path="/messages" element={<FacilityMessagesPage />} /><Route path="/treat-abroad" element={<TreatAbroadPage />} /><Route path="/queue" element={<QueuePage />} /><Route path="/mch" element={<MCHPage />} /><Route path="/benefits" element={<BenefitPackagesPage />} /><Route path="/laboratory" element={<LaboratoryWorkflowPage />} /><Route path="/pharmacy" element={<PharmacyPage />} /><Route path="/billing" element={<BillingPage />} /><Route path="/claims" element={<ClaimsPage />} /><Route path="/referrals" element={<ReferralsPage />} /><Route path="/reports" element={<ReportsPage />} />
        </Route>
      </Route>
    </Route>
    <Route path="*" element={<Navigate to="/login" replace />} />
  </Routes></BrowserRouter></WorkspaceProvider></AuthProvider>;
}
