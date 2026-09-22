"""Hospital OS — encounter journey spine + orphan prevention checks."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.encounters.models import Encounter
from app.hospital_os.schemas import (
    EncounterJourney,
    FacilityIntegrityReport,
    OrphanFinding,
    StageStatus,
)
from app.patients.models import PatientFacility, Person


def _count(db: Session, model, **filters) -> int:
    try:
        q = select(func.count()).select_from(model)
        for k, v in filters.items():
            q = q.where(getattr(model, k) == v)
        return int(db.scalar(q) or 0)
    except Exception:
        return 0


def get_encounter_journey(db: Session, encounter_id: UUID, facility_id: UUID) -> EncounterJourney:
    enc = db.get(Encounter, encounter_id)
    if enc is None or enc.facility_id != facility_id:
        raise ValueError("ENCOUNTER_NOT_FOUND")

    stages: list[StageStatus] = []
    blockers: list[str] = []

    # 1 Registration / enrollment
    enrolled = db.scalar(
        select(PatientFacility.id).where(
            PatientFacility.patient_id == enc.patient_id,
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
        )
    )
    stages.append(
        StageStatus(
            code="REGISTRATION",
            label="Registration / enrollment",
            complete=enrolled is not None,
            count=1 if enrolled else 0,
            notes=[] if enrolled else ["Patient not actively enrolled at this facility"],
        )
    )
    if not enrolled:
        blockers.append("Enroll patient before clinical work")

    # 2 Encounter open
    stages.append(
        StageStatus(
            code="ENCOUNTER",
            label="Encounter",
            complete=True,
            count=1,
            notes=[f"Status: {enc.status}"],
        )
    )

    # 3 Vitals
    vitals_n = 0
    try:
        from app.clinical.models import Vital

        vitals_n = _count(db, Vital, encounter_id=encounter_id)
    except Exception:
        pass
    stages.append(
        StageStatus(
            code="VITALS",
            label="Vitals / triage",
            complete=vitals_n > 0,
            count=vitals_n,
        )
    )

    # 4 Consultation
    consult_n = 0
    try:
        from app.clinical.models import Consultation

        consult_n = _count(db, Consultation, encounter_id=encounter_id)
    except Exception:
        pass
    stages.append(
        StageStatus(
            code="CONSULTATION",
            label="Consultation",
            complete=consult_n > 0,
            count=consult_n,
        )
    )

    # 5 Diagnosis
    dx_n = 0
    try:
        from app.clinical.models import Diagnosis

        dx_n = _count(db, Diagnosis, encounter_id=encounter_id)
    except Exception:
        pass
    stages.append(
        StageStatus(
            code="DIAGNOSIS",
            label="Diagnosis",
            complete=dx_n > 0,
            count=dx_n,
        )
    )

    # 6 Lab
    lab_n = 0
    try:
        from app.laboratory.models import LabOrder

        lab_n = _count(db, LabOrder, encounter_id=encounter_id)
    except Exception:
        pass
    stages.append(
        StageStatus(
            code="LABORATORY",
            label="Laboratory orders",
            complete=lab_n > 0,
            count=lab_n,
            notes=["Optional depending on clinical need"] if lab_n == 0 else [],
        )
    )

    # 7 Radiology
    rad_n = 0
    try:
        from app.radiology.models import ImagingOrder

        rad_n = _count(db, ImagingOrder, encounter_id=encounter_id)
    except Exception:
        pass
    stages.append(
        StageStatus(
            code="RADIOLOGY",
            label="Radiology orders",
            complete=rad_n > 0,
            count=rad_n,
            notes=["Optional"] if rad_n == 0 else [],
        )
    )

    # 8 Prescription
    rx_n = 0
    try:
        from app.pharmacy.models import Prescription

        rx_n = _count(db, Prescription, encounter_id=encounter_id)
    except Exception:
        pass
    stages.append(
        StageStatus(
            code="PHARMACY",
            label="Prescriptions",
            complete=rx_n > 0,
            count=rx_n,
            notes=["Optional"] if rx_n == 0 else [],
        )
    )

    # 9 Billing charges
    charge_n = 0
    try:
        from app.billing.models import Charge

        charge_n = _count(db, Charge, encounter_id=encounter_id)
    except Exception:
        pass
    stages.append(
        StageStatus(
            code="BILLING",
            label="Charges",
            complete=charge_n > 0,
            count=charge_n,
        )
    )

    # 10 Invoice
    inv_n = 0
    try:
        from app.billing.models import Invoice

        inv_n = _count(db, Invoice, encounter_id=encounter_id)
    except Exception:
        pass
    stages.append(
        StageStatus(
            code="INVOICE",
            label="Invoice",
            complete=inv_n > 0,
            count=inv_n,
        )
    )
    if charge_n > 0 and inv_n == 0:
        blockers.append("Charges exist without invoice — create invoice before claim")

    # 11 Claim
    claim_n = 0
    try:
        from app.claims.models import Claim
        from app.billing.models import Invoice

        inv_ids = list(
            db.scalars(select(Invoice.id).where(Invoice.encounter_id == encounter_id))
        )
        if inv_ids:
            claim_n = int(
                db.scalar(
                    select(func.count())
                    .select_from(Claim)
                    .where(Claim.invoice_id.in_(inv_ids))
                )
                or 0
            )
    except Exception:
        pass
    stages.append(
        StageStatus(
            code="CLAIM",
            label="Claim",
            complete=claim_n > 0,
            count=claim_n,
            notes=["Required for insured encounters"] if inv_n > 0 and claim_n == 0 else [],
        )
    )

    # Next recommended
    next_rec = None
    order = [
        "REGISTRATION",
        "ENCOUNTER",
        "VITALS",
        "CONSULTATION",
        "DIAGNOSIS",
        "LABORATORY",
        "RADIOLOGY",
        "PHARMACY",
        "BILLING",
        "INVOICE",
        "CLAIM",
    ]
    # Prefer incomplete clinical before billing
    priority = ["REGISTRATION", "VITALS", "CONSULTATION", "DIAGNOSIS", "BILLING", "INVOICE", "CLAIM"]
    by_code = {s.code: s for s in stages}
    for code in priority:
        st = by_code.get(code)
        if st and not st.complete:
            next_rec = code
            break
    if next_rec is None and enc.status == "OPEN":
        next_rec = "CLOSE_ENCOUNTER"

    integrity_ok = len(blockers) == 0 and enrolled is not None

    return EncounterJourney(
        encounter_id=enc.id,
        patient_id=enc.patient_id,
        facility_id=enc.facility_id,
        status=enc.status,
        stages=stages,
        next_recommended=next_rec,
        blockers=blockers,
        integrity_ok=integrity_ok,
    )


def scan_facility_orphans(
    db: Session, facility_id: UUID, *, limit: int = 100
) -> FacilityIntegrityReport:
    """Find orphan clinical/financial records for a facility."""
    findings: list[OrphanFinding] = []
    limit = min(max(limit, 1), 500)

    encounters = list(
        db.scalars(
            select(Encounter)
            .where(Encounter.facility_id == facility_id)
            .order_by(Encounter.created_at.desc())
            .limit(limit)
        )
    )

    for enc in encounters:
        # Charge without matching patient
        try:
            from app.billing.models import Charge

            for ch in db.scalars(
                select(Charge).where(Charge.encounter_id == enc.id).limit(50)
            ):
                if getattr(ch, "patient_id", None) and ch.patient_id != enc.patient_id:
                    findings.append(
                        OrphanFinding(
                            resource_type="CHARGE",
                            resource_id=str(ch.id),
                            issue="Charge patient_id does not match encounter patient",
                            severity="BLOCKER",
                        )
                    )
        except Exception:
            pass

        # Prescription without encounter patient match
        try:
            from app.pharmacy.models import Prescription

            for rx in db.scalars(
                select(Prescription).where(Prescription.encounter_id == enc.id).limit(50)
            ):
                pid = getattr(rx, "patient_id", None)
                if pid and pid != enc.patient_id:
                    findings.append(
                        OrphanFinding(
                            resource_type="PRESCRIPTION",
                            resource_id=str(rx.id),
                            issue="Prescription patient mismatch vs encounter",
                            severity="BLOCKER",
                        )
                    )
        except Exception:
            pass

        # Invoice without charges
        try:
            from app.billing.models import Charge, Invoice

            for inv in db.scalars(
                select(Invoice).where(Invoice.encounter_id == enc.id).limit(20)
            ):
                cn = _count(db, Charge, encounter_id=enc.id)
                if cn == 0:
                    findings.append(
                        OrphanFinding(
                            resource_type="INVOICE",
                            resource_id=str(inv.id),
                            issue="Invoice has no charges on encounter",
                            severity="WARNING",
                        )
                    )
        except Exception:
            pass

    # Claims pointing at missing invoices (sample recent claims if model allows facility)
    try:
        from app.billing.models import Invoice
        from app.claims.models import Claim

        inv_ids = set(
            db.scalars(
                select(Invoice.id).where(Invoice.facility_id == facility_id).limit(500)
            )
        )
        for cl in db.scalars(select(Claim).order_by(Claim.created_at.desc()).limit(200)):
            iid = getattr(cl, "invoice_id", None)
            fid = getattr(cl, "facility_id", None)
            if fid and fid != facility_id:
                continue
            if iid and inv_ids and iid not in inv_ids:
                # only flag if we loaded invoices and facility filter present
                if fid == facility_id:
                    findings.append(
                        OrphanFinding(
                            resource_type="CLAIM",
                            resource_id=str(cl.id),
                            issue="Claim invoice not found in facility invoice set",
                            severity="BLOCKER",
                        )
                    )
    except Exception:
        pass

    ok = not any(f.severity == "BLOCKER" for f in findings)
    summary = (
        "No blocker orphans detected in sample."
        if ok
        else f"{sum(1 for f in findings if f.severity == 'BLOCKER')} blocker issue(s) found."
    )

    record_audit(
        db,
        action="HOSPITAL_OS_INTEGRITY_SCAN",
        resource_type="FACILITY",
        resource_id=str(facility_id),
        result="OK" if ok else "ISSUES",
        facility_id=facility_id,
        metadata={"findings": len(findings), "encounters": len(encounters)},
        commit=False,
    )

    return FacilityIntegrityReport(
        facility_id=facility_id,
        scanned_at=datetime.now(timezone.utc),
        encounters_checked=len(encounters),
        findings=findings,
        integrity_ok=ok,
        summary=summary,
    )


def assert_can_create_claim_for_invoice(
    db: Session, *, invoice_id: UUID, facility_id: UUID
) -> None:
    """Hard gate: claim only if invoice belongs to facility and has encounter linkage."""
    from app.billing.models import Invoice

    inv = db.get(Invoice, invoice_id)
    if inv is None:
        raise ValueError("INVOICE_NOT_FOUND")
    if getattr(inv, "facility_id", None) != facility_id:
        raise ValueError("INVOICE_FACILITY_MISMATCH")
    if not getattr(inv, "encounter_id", None):
        raise ValueError("INVOICE_MISSING_ENCOUNTER")
    enc = db.get(Encounter, inv.encounter_id)
    if enc is None or enc.facility_id != facility_id:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    person = db.get(Person, enc.patient_id)
    if person is None or person.status == "DECEASED":
        raise ValueError("PATIENT_NOT_CLAIMABLE")
