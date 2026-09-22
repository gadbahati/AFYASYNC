"""Composite quality scorecard from live operational tables."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ambulance.models import AmbulanceRequest
from app.emergency.models import EmergencyVisit
from app.facilities.models import Facility
from app.pharmacy.models import InventoryItem
from app.rbac.models import Staff
from app.referrals.models import Referral
from app.surveillance.models import NotifiableEvent
from app.telemedicine.models import TeleConsultRequest
from app.workforce.models import ProfessionalCredential


def _band(score: float) -> str:
    if score >= 80:
        return "GREEN"
    if score >= 60:
        return "AMBER"
    return "RED"


def facility_scorecard(db: Session, *, facility_id: UUID, days: int = 30) -> dict:
    days = max(7, min(days, 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    since_date = date.today() - timedelta(days=days)

    fac = db.get(Facility, facility_id)
    if fac is None:
        raise ValueError("FACILITY_NOT_FOUND")

    # --- Workforce licence coverage ---
    active_staff = db.scalar(
        select(func.count()).select_from(Staff).where(
            Staff.facility_id == facility_id, Staff.status == "ACTIVE"
        )
    ) or 0
    staff_with_cred = db.scalar(
        select(func.count(func.distinct(ProfessionalCredential.staff_id))).where(
            ProfessionalCredential.facility_id == facility_id,
            ProfessionalCredential.status == "ACTIVE",
        )
    ) or 0
    workforce_pct = (100.0 * staff_with_cred / active_staff) if active_staff else 100.0

    # --- Inventory stock health ---
    inv_total = db.scalar(
        select(func.count()).select_from(InventoryItem).where(
            InventoryItem.facility_id == facility_id,
            InventoryItem.status == "ACTIVE",
        )
    ) or 0
    inv_low = db.scalar(
        select(func.count()).select_from(InventoryItem).where(
            InventoryItem.facility_id == facility_id,
            InventoryItem.status == "ACTIVE",
            InventoryItem.current_quantity <= InventoryItem.minimum_quantity,
        )
    ) or 0
    stock_ok_pct = (100.0 * (inv_total - inv_low) / inv_total) if inv_total else 100.0

    # --- Emergency open load (lower is better for score) ---
    open_er = db.scalar(
        select(func.count()).select_from(EmergencyVisit).where(
            EmergencyVisit.facility_id == facility_id,
            EmergencyVisit.status.in_(["WAITING", "TRIAGED", "IN_CARE", "ACTIVE", "OPEN", "BEING_SEEN"]),
        )
    ) or 0
    er_score = max(0.0, 100.0 - min(open_er, 50) * 2)  # 0 open = 100, 50+ open = 0

    # --- Open referrals outbound ---
    open_ref = db.scalar(
        select(func.count()).select_from(Referral).where(
            Referral.source_facility_id == facility_id,
            Referral.status.in_(["CREATED", "SENT", "ACCEPTED", "IN_TRANSIT", "PENDING"]),
        )
    ) or 0
    ref_score = max(0.0, 100.0 - min(open_ref, 30) * 3)

    # --- Surveillance: open notifiable ---
    open_notif = db.scalar(
        select(func.count()).select_from(NotifiableEvent).where(
            NotifiableEvent.facility_id == facility_id,
            NotifiableEvent.status.in_(["OPEN", "SUBMITTED"]),
            NotifiableEvent.notification_date >= since_date,
        )
    ) or 0
    # Reporting is good; unclosed backlog is the penalty
    notif_reported = db.scalar(
        select(func.count()).select_from(NotifiableEvent).where(
            NotifiableEvent.facility_id == facility_id,
            NotifiableEvent.notification_date >= since_date,
        )
    ) or 0
    notif_score = 100.0 if notif_reported == 0 else max(40.0, 100.0 - min(open_notif, 20) * 3)

    # --- Ambulance / telemedicine activity (presence, not volume pressure) ---
    amb_open = db.scalar(
        select(func.count()).select_from(AmbulanceRequest).where(
            AmbulanceRequest.facility_id == facility_id,
            AmbulanceRequest.status.in_(["REQUESTED", "DISPATCHED", "EN_ROUTE", "ARRIVED"]),
        )
    ) or 0
    tele_open = db.scalar(
        select(func.count()).select_from(TeleConsultRequest).where(
            TeleConsultRequest.facility_id == facility_id,
            TeleConsultRequest.status.in_(["REQUESTED", "ACCEPTED"]),
        )
    ) or 0

    # Weighted composite
    composite = (
        workforce_pct * 0.25
        + stock_ok_pct * 0.25
        + er_score * 0.20
        + ref_score * 0.15
        + notif_score * 0.15
    )
    composite = round(min(100.0, max(0.0, composite)), 1)

    metrics = [
        {"code": "WORKFORCE_LICENCE", "label": "Staff with active licence on file", "value": round(workforce_pct, 1), "unit": "%", "weight": 0.25},
        {"code": "STOCK_OK", "label": "SKUs at or above minimum", "value": round(stock_ok_pct, 1), "unit": "%", "weight": 0.25},
        {"code": "ER_LOAD", "label": "ER load score (higher = lighter load)", "value": round(er_score, 1), "unit": "pts", "weight": 0.20},
        {"code": "REFERRAL_FLOW", "label": "Referral backlog score", "value": round(ref_score, 1), "unit": "pts", "weight": 0.15},
        {"code": "SURVEILLANCE", "label": "Notifiable case handling score", "value": round(notif_score, 1), "unit": "pts", "weight": 0.15},
    ]

    return {
        "facility_id": str(facility_id),
        "facility_name": getattr(fac, "name", None),
        "county": getattr(fac, "county", None),
        "window_days": days,
        "composite_score": composite,
        "band": _band(composite),
        "metrics": metrics,
        "operational_snapshot": {
            "active_staff": int(active_staff),
            "staff_with_credential": int(staff_with_cred),
            "inventory_skus": int(inv_total),
            "inventory_low_stock": int(inv_low),
            "open_emergency_visits": int(open_er),
            "open_outbound_referrals": int(open_ref),
            "open_notifiable_events": int(open_notif),
            "notifiable_reported_in_window": int(notif_reported),
            "open_ambulance": int(amb_open),
            "open_teleconsult": int(tele_open),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Composite is operational readiness — not a clinical quality accreditation score",
        "developer": "BAHATI GAD WANGWE",
    }


def national_scorecard(db: Session, *, days: int = 30, limit: int = 50) -> dict:
    days = max(7, min(days, 90))
    limit = max(1, min(limit, 100))
    facilities = list(
        db.scalars(
            select(Facility).where(Facility.status == "ACTIVE").order_by(Facility.name).limit(limit)
        )
    )
    cards = []
    bands = {"GREEN": 0, "AMBER": 0, "RED": 0}
    for fac in facilities:
        try:
            card = facility_scorecard(db, facility_id=fac.id, days=days)
            cards.append(
                {
                    "facility_id": card["facility_id"],
                    "facility_name": card["facility_name"],
                    "county": card["county"],
                    "composite_score": card["composite_score"],
                    "band": card["band"],
                }
            )
            bands[card["band"]] = bands.get(card["band"], 0) + 1
        except Exception:
            continue

    cards.sort(key=lambda x: -x["composite_score"])
    avg = round(sum(c["composite_score"] for c in cards) / len(cards), 1) if cards else 0.0

    return {
        "window_days": days,
        "facility_count": len(cards),
        "average_composite": avg,
        "bands": bands,
        "facilities": cards,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
