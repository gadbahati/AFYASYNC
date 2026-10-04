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
import { FacilityLoginPage } from "./pages/FacilityLoginPage";
import { GovernmentLoginPage } from "./pages/GovernmentLoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EncountersPage } from "./pages/EncountersPage";
import { ClinicalWorklistPage } from "./pages/ClinicalWorklistPage";
import { EncounterDetailPage } from "./pages/EncounterDetailPage";
import { PatientsPage } from "./pages/PatientsPage";
import { PatientDetailPage } from "./pages/PatientDetailPage";
import { NewEncounterPage } from "./pages/NewEncounterPage";
import { WorkspacePage } from "./pages/WorkspacePage";
import { LaboratoryWorkflowPage } from "./pages/LaboratoryWorkflowPage";
import { PharmacyPage } from "./pages/PharmacyPage";
import { RadiologyPage } from "./pages/RadiologyPage";
import { ClaimsPage } from "./pages/ClaimsPage";
import { BillingPage } from "./pages/BillingPage";
import { AppointmentsPage } from "./pages/AppointmentsPage";
import { MCHPage } from "./pages/MCHPage";
import { FacilityMessagesPage } from "./pages/FacilityMessagesPage";
import { ReferralsPage } from "./pages/ReferralsPage";

/** Phase 149 — facility routes with real Referrals page.
 *  Full tree: python3 scripts/merge_app_routes.py
 *  Developed by BAHATI GAD WANGWE.
 */
export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <WorkspaceProvider>
          <GlobalCommand />
          <Routes>
            <Route path="/" element={<EntryPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/login/patient" element={<PatientLoginPage />} />
            <Route path="/login/facility" element={<FacilityLoginPage />} />
            <Route path="/login/government" element={<GovernmentLoginPage />} />
            <Route
              path="/*"
              element={
                <ProtectedRoute>
                  <Layout>
                    <Routes>
                      <Route path="/" element={<DashboardPage />} />
                      <Route path="/workspace" element={<WorkspacePage />} />
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
                      <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                  </Layout>
                </ProtectedRoute>
              }
            />
            <Route
              path="/government/*"
              element={
                <GovernmentProtectedRoute>
                  <Layout>
                    <DashboardPage />
                  </Layout>
                </GovernmentProtectedRoute>
              }
            />
          </Routes>
        </WorkspaceProvider>
      </BrowserRouter>
    </AuthProvider>
  );
}
