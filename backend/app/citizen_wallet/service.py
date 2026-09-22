"""Citizen-facing coverage, utilisation and charge transparency — hardened."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.models import Charge, Invoice
from app.coverage.models import Coverage, Payer
from app.coverage.utilisation_models import BenefitUtilisation
from app.patients.models import AfyaIdentity, Person


def _dec(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(Decimal(str(v)))
    except Exception:
        return 0.0


def _iso(dt) -> str | None:
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def wallet_overview(db: Session, *, person_id: UUID) -> dict:
    person = db.get(Person, person_id)
    if person is None:
        raise ValueError("PERSON_NOT_FOUND")

    identity = db.scalar(
        select(AfyaIdentity).where(
            AfyaIdentity.person_id == person_id,
            AfyaIdentity.status == "ACTIVE",
        )
    )

    coverages = list(
        db.execute(
            select(Coverage, Payer)
            .join(Payer, Payer.id == Coverage.payer_id)
            .where(Coverage.person_id == person_id)
            .order_by(Coverage.created_at.desc())
            .limit(20)
        ).all()
    )

    year = date.today().year
    util_rows = list(
        db.execute(
            select(
                BenefitUtilisation.service_code,
                func.coalesce(func.sum(BenefitUtilisation.amount), 0),
                func.count(),
            )
            .where(
                BenefitUtilisation.person_id == person_id,
                BenefitUtilisation.calendar_year == year,
                BenefitUtilisation.status == "POSTED",
            )
            .group_by(BenefitUtilisation.service_code)
        ).all()
    )

    invoices = list(
        db.scalars(
            select(Invoice)
            .where(Invoice.patient_id == person_id)
            .order_by(Invoice.created_at.desc())
            .limit(10)
        )
    )

    open_balance = 0.0
    inv_out = []
    for inv in invoices:
        total = _dec(getattr(inv, "total_amount", None))
        patient_amt = _dec(getattr(inv, "patient_amount", None))
        status = str(getattr(inv, "status", "") or "").upper()
        remaining = 0.0 if status in {"PAID", "SETTLED", "CLOSED", "CANCELLED"} else max(patient_amt, 0.0)
        if remaining == 0.0 and status in {"OPEN", "PARTIAL", "ISSUED", "ACTIVE"}:
            remaining = max(total, 0.0)
        open_balance += remaining
        inv_out.append(
            {
                "invoice_id": str(inv.id),
                "invoice_number": getattr(inv, "invoice_id", None) or str(inv.id),
                "status": getattr(inv, "status", None),
                "total_amount": total,
                "patient_amount": patient_amt,
                "open_amount": remaining,
                "created_at": _iso(getattr(inv, "created_at", None)),
            }
        )

    coverage_out = []
    for cov, payer in coverages:
        coverage_out.append(
            {
                "coverage_id": str(cov.id),
                "payer_code": getattr(payer, "code", None),
                "payer_name": getattr(payer, "name", None),
                "membership_number": getattr(cov, "membership_number", None),
                "status": getattr(cov, "status", None),
                "verification_status": getattr(cov, "verification_status", None),
                "start_date": _iso(getattr(cov, "start_date", None)),
                "end_date": _iso(getattr(cov, "end_date", None)),
            }
        )

    utilisation = [
        {"service_code": code, "amount_used": _dec(amt), "events": int(cnt)}
        for code, amt, cnt in util_rows
    ]
    utilisation.sort(key=lambda x: -x["amount_used"])

    return {
        "person_id": str(person_id),
        "afya_id": getattr(identity, "afya_id", None) if identity else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coverages": coverage_out,
        "utilisation_year": year,
        "utilisation_by_service": utilisation[:40],
        "utilisation_total": round(sum(u["amount_used"] for u in utilisation), 2),
        "recent_invoices": inv_out,
        "estimated_open_balance": round(open_balance, 2),
        "privacy": "Patient-owned view of own coverage and charges only",
        "developer": "BAHATI GAD WANGWE",
    }


def benefits_transparency(db: Session, *, person_id: UUID) -> dict:
    overview = wallet_overview(db, person_id=person_id)
    active_payers = [
        c
        for c in overview["coverages"]
        if str(c.get("status") or "").upper() in {"ACTIVE", "VERIFIED", "VALID", "APPROVED"}
    ]
    return {
        "person_id": str(person_id),
        "active_coverage_count": len(active_payers),
        "coverages": overview["coverages"],
        "utilisation_year": overview["utilisation_year"],
        "utilisation_by_service": overview["utilisation_by_service"],
        "guidance": [
            "Coverage on file is local until verified against SHA live connector",
            "Use Can I Get This? at facility for service-level simulation",
            "Open balance is facility billing (patient_amount), not national benefit balance",
        ],
        "sha_live": "Requires SHA_DHA_MODE=live and authorised tokens",
        "generated_at": overview["generated_at"],
        "developer": "BAHATI GAD WANGWE",
    }


def charge_ledger(db: Session, *, person_id: UUID, limit: int = 50) -> dict:
    limit = max(1, min(limit, 100))
    charges = list(
        db.scalars(
            select(Charge)
            .where(Charge.patient_id == person_id)
            .order_by(Charge.created_at.desc())
            .limit(limit)
        )
    )
    items = []
    for ch in charges:
        items.append(
            {
                "charge_id": str(ch.id),
                "charge_number": getattr(ch, "charge_id", None),
                "description": getattr(ch, "description", None)
                or getattr(ch, "service_name", None)
                or getattr(ch, "charge_id", None),
                "amount": _dec(getattr(ch, "total_amount", None) or getattr(ch, "amount", None)),
                "quantity": _dec(getattr(ch, "quantity", None)),
                "status": getattr(ch, "status", None),
                "created_at": _iso(getattr(ch, "created_at", None)),
            }
        )
    return {
        "person_id": str(person_id),
        "count": len(items),
        "charges": items,
        "developer": "BAHATI GAD WANGWE",
    }
