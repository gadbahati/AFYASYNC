from datetime import datetime, timezone

from app.patients.timeline_router import _build_events


def test_timeline_merges_billing_claims_and_clinical_events_in_reverse_chronological_order():
    record = {
        "encounters": [{
            "id": "enc-1",
            "encounter_id": "ENC-001",
            "started_at": datetime(2026, 1, 1, 8, tzinfo=timezone.utc),
            "status": "CLOSED",
            "department_name": "OPD",
            "type": "OUTPATIENT",
            "reason": "Review",
            "consultation": None,
            "vitals": [],
            "diagnoses": [],
        }],
        "care_plans": [],
        "laboratory": [],
        "prescriptions": [],
        "medication_actions": [],
        "admissions": [],
        "preauthorizations": [],
        "appointments": [],
        "queue_history": [],
        "referrals": [],
        "transfers": [],
        "billing": {
            "charges": [{
                "id": "charge-1",
                "charge_id": "CHG-001",
                "encounter_id": "enc-1",
                "service_code": "CONSULT",
                "service_name": "Consultation",
                "quantity": 1,
                "total_amount": 500,
                "status": "POSTED",
                "created_at": datetime(2026, 1, 1, 9, tzinfo=timezone.utc),
            }],
            "invoices": [{
                "id": "invoice-1",
                "invoice_id": "INV-001",
                "encounter_id": "enc-1",
                "total_amount": 500,
                "payer_amount": 500,
                "patient_amount": 0,
                "status": "SUBMITTED",
                "created_at": datetime(2026, 1, 1, 10, tzinfo=timezone.utc),
            }],
            "payments": [{
                "id": "payment-1",
                "transaction_id": "TX-001",
                "invoice_id": "invoice-1",
                "amount": 500,
                "payment_method": "SHA",
                "provider": "SHA",
                "status": "CONFIRMED",
                "created_at": datetime(2026, 1, 1, 11, tzinfo=timezone.utc),
                "confirmed_at": datetime(2026, 1, 1, 12, tzinfo=timezone.utc),
            }],
        },
        "claims": [{
            "id": "claim-1",
            "claim_id": "CLM-001",
            "encounter_id": "enc-1",
            "payer_name": "SHA",
            "claim_amount": 500,
            "approved_amount": 500,
            "paid_amount": 500,
            "status": "PAID",
            "submitted_at": datetime(2026, 1, 1, 13, tzinfo=timezone.utc),
            "responses": [{
                "id": "response-1",
                "external_reference": "EXT-001",
                "status": "APPROVED",
                "response_code": "00",
                "response_message": "Approved",
                "received_at": datetime(2026, 1, 1, 14, tzinfo=timezone.utc),
            }],
            "reconciliation": {
                "id": "recon-1",
                "expected_amount": 500,
                "received_amount": 500,
                "difference": 0,
                "status": "RECONCILED",
                "reconciled_at": datetime(2026, 1, 1, 15, tzinfo=timezone.utc),
            },
        }],
    }

    events = _build_events(record)

    assert [event.type for event in events] == [
        "CLAIM_RECONCILIATION",
        "CLAIM_RESPONSE",
        "CLAIM",
        "PAYMENT",
        "INVOICE",
        "CHARGE",
        "ENCOUNTER",
    ]
    assert events[0].metadata["difference"] == 0
    assert events[2].metadata["claim_amount"] == 500
    assert events[3].metadata["payment_method"] == "SHA"


def test_timeline_ignores_events_without_timestamps():
    events = _build_events({
        "encounters": [],
        "care_plans": [],
        "laboratory": [],
        "prescriptions": [],
        "medication_actions": [],
        "admissions": [],
        "preauthorizations": [],
        "appointments": [],
        "queue_history": [],
        "referrals": [],
        "transfers": [],
        "billing": {"charges": [], "invoices": [], "payments": []},
        "claims": [{
            "id": "claim-1",
            "claim_id": "CLM-001",
            "encounter_id": None,
            "payer_name": "SHA",
            "claim_amount": 100,
            "approved_amount": 0,
            "paid_amount": 0,
            "status": "PENDING",
            "submitted_at": None,
            "responses": [],
            "reconciliation": None,
        }],
    })

    assert events == []
