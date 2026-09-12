import { FeatureListPage } from "./FeatureListPage";

export function LabPage() {
  return (
    <FeatureListPage
      title="Laboratory"
      subtitle="Orders and results"
      columns={[
        { key: "order", label: "Order" },
        { key: "patient", label: "Patient" },
        { key: "tests", label: "Tests" },
        { key: "priority", label: "Priority" },
        { key: "status", label: "Status" },
      ]}
      rows={[
        { order: "LAB-1001", patient: "Amina Wanjiku", tests: "FBC, Malaria", priority: "ROUTINE", status: "ORDERED" },
        { order: "LAB-1002", patient: "Brian Ochieng", tests: "RBS", priority: "STAT", status: "IN_PROGRESS" },
        { order: "LAB-1003", patient: "Faith Mwangi", tests: "Urinalysis", priority: "ROUTINE", status: "RESULTED" },
      ]}
    />
  );
}

export function PharmacyPage() {
  return (
    <FeatureListPage
      title="Pharmacy"
      subtitle="Prescriptions and dispense queue"
      columns={[
        { key: "rx", label: "Rx" },
        { key: "patient", label: "Patient" },
        { key: "items", label: "Items" },
        { key: "status", label: "Status" },
      ]}
      rows={[
        { rx: "RX-501", patient: "Amina Wanjiku", items: "Amoxicillin 500mg × 21", status: "PENDING" },
        { rx: "RX-502", patient: "Brian Ochieng", items: "Paracetamol 500mg × 20", status: "DISPENSED" },
        { rx: "RX-503", patient: "Faith Mwangi", items: "ORS sachets × 4", status: "PENDING" },
      ]}
    />
  );
}

export function BillingPage() {
  return (
    <FeatureListPage
      title="Billing"
      subtitle="Charges, invoices and payments"
      columns={[
        { key: "invoice", label: "Invoice" },
        { key: "patient", label: "Patient" },
        { key: "amount", label: "Amount (KES)" },
        { key: "payer", label: "Payer" },
        { key: "status", label: "Status" },
      ]}
      rows={[
        { invoice: "INV-9001", patient: "Amina Wanjiku", amount: "2,500", payer: "SHA", status: "OPEN" },
        { invoice: "INV-9002", patient: "Brian Ochieng", amount: "1,200", payer: "Cash", status: "PAID" },
        { invoice: "INV-9003", patient: "Faith Mwangi", amount: "3,800", payer: "SHA", status: "PARTIAL" },
      ]}
    />
  );
}

export function ClaimsPage() {
  return (
    <FeatureListPage
      title="Claims"
      subtitle="Payer claim submission and reconciliation"
      columns={[
        { key: "claim", label: "Claim" },
        { key: "patient", label: "Patient" },
        { key: "amount", label: "Amount (KES)" },
        { key: "payer", label: "Payer" },
        { key: "status", label: "Status" },
      ]}
      rows={[
        { claim: "CLM-3001", patient: "Amina Wanjiku", amount: "2,500", payer: "SHA", status: "SUBMITTED" },
        { claim: "CLM-3002", patient: "Faith Mwangi", amount: "3,800", payer: "SHA", status: "APPROVED" },
        { claim: "CLM-3003", patient: "Brian Ochieng", amount: "900", payer: "SHA", status: "PAID" },
      ]}
    />
  );
}

export function ReferralsPage() {
  return (
    <FeatureListPage
      title="Referrals & transfers"
      subtitle="Outbound and inbound patient movement"
      columns={[
        { key: "ref", label: "Referral" },
        { key: "patient", label: "Patient" },
        { key: "from", label: "From" },
        { key: "to", label: "To" },
        { key: "status", label: "Status" },
      ]}
      rows={[
        { ref: "REF-701", patient: "Amina Wanjiku", from: "Pilot OPD", to: "County Referral", status: "PENDING" },
        { ref: "REF-702", patient: "Brian Ochieng", from: "A&E", to: "Surgical Ward", status: "ACCEPTED" },
        { ref: "REF-703", patient: "Faith Mwangi", from: "Pilot OPD", to: "Lab Hub", status: "COMPLETED" },
      ]}
    />
  );
}
