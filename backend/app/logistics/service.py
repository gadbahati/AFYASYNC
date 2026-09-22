"""Logistics intelligence on top of live inventory — no invented stock levels."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.facilities.models import Facility
from app.pharmacy.models import InventoryItem, Medication


def _risk_level(current: float, minimum: float) -> str:
    if minimum <= 0:
        if current <= 0:
            return "CRITICAL"
        return "UNKNOWN"
    ratio = current / minimum
    if current <= 0:
        return "STOCKOUT"
    if ratio <= 0.5:
        return "CRITICAL"
    if ratio <= 1.0:
        return "LOW"
    if ratio <= 1.5:
        return "WATCH"
    return "OK"


def stockout_board(
    db: Session,
    *,
    county: str | None = None,
    limit: int = 100,
) -> dict:
    limit = max(1, min(limit, 300))
    q = (
        select(InventoryItem, Facility, Medication)
        .join(Facility, Facility.id == InventoryItem.facility_id)
        .join(Medication, Medication.id == InventoryItem.medication_id)
        .where(
            Facility.status == "ACTIVE",
            InventoryItem.status == "ACTIVE",
            Medication.status == "ACTIVE",
        )
    )
    if county:
        q = q.where(Facility.county == county.strip())

    rows = db.execute(q.limit(2000)).all()
    items = []
    counts = defaultdict(int)
    for inv, fac, med in rows:
        cur = float(inv.current_quantity or 0)
        mn = float(inv.minimum_quantity or 0)
        risk = _risk_level(cur, mn)
        counts[risk] += 1
        if risk in {"STOCKOUT", "CRITICAL", "LOW"}:
            items.append(
                {
                    "facility_id": str(fac.id),
                    "facility_name": fac.name,
                    "county": fac.county,
                    "medication_code": med.code,
                    "medication_name": med.name,
                    "current_quantity": cur,
                    "minimum_quantity": mn,
                    "risk": risk,
                }
            )

    items.sort(key=lambda x: {"STOCKOUT": 0, "CRITICAL": 1, "LOW": 2}.get(x["risk"], 9))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "county": county,
        "risk_counts": dict(counts),
        "at_risk_count": len(items),
        "items": items[:limit],
        "developer": "BAHATI GAD WANGWE",
    }


def redistribution_suggestions(
    db: Session,
    *,
    county: str | None = None,
    limit: int = 50,
) -> dict:
    """Suggest moves from surplus facilities to shortage facilities for same medication."""
    limit = max(1, min(limit, 100))
    q = (
        select(InventoryItem, Facility, Medication)
        .join(Facility, Facility.id == InventoryItem.facility_id)
        .join(Medication, Medication.id == InventoryItem.medication_id)
        .where(
            Facility.status == "ACTIVE",
            InventoryItem.status == "ACTIVE",
            Medication.status == "ACTIVE",
        )
    )
    if county:
        q = q.where(Facility.county == county.strip())

    by_med: dict[str, list] = defaultdict(list)
    for inv, fac, med in db.execute(q.limit(3000)).all():
        cur = float(inv.current_quantity or 0)
        mn = float(inv.minimum_quantity or 0)
        surplus = max(0.0, cur - max(mn * 1.5, mn + 10))
        deficit = max(0.0, mn - cur) if mn > 0 else (1.0 if cur <= 0 else 0.0)
        by_med[med.code].append(
            {
                "facility_id": str(fac.id),
                "facility_name": fac.name,
                "county": fac.county,
                "medication_code": med.code,
                "medication_name": med.name,
                "current": cur,
                "minimum": mn,
                "surplus": surplus,
                "deficit": deficit,
            }
        )

    suggestions = []
    for code, sites in by_med.items():
        donors = sorted([s for s in sites if s["surplus"] > 0], key=lambda x: -x["surplus"])
        needers = sorted([s for s in sites if s["deficit"] > 0], key=lambda x: -x["deficit"])
        if not donors or not needers:
            continue
        for need in needers:
            for donor in donors:
                if donor["facility_id"] == need["facility_id"]:
                    continue
                qty = min(donor["surplus"], need["deficit"])
                if qty <= 0:
                    continue
                suggestions.append(
                    {
                        "medication_code": code,
                        "medication_name": need["medication_name"],
                        "from_facility_id": donor["facility_id"],
                        "from_facility_name": donor["facility_name"],
                        "to_facility_id": need["facility_id"],
                        "to_facility_name": need["facility_name"],
                        "suggested_quantity": round(qty, 2),
                        "reason": "Balance surplus to cover deficit vs minimum",
                    }
                )
                donor["surplus"] -= qty
                need["deficit"] -= qty
                if len(suggestions) >= limit:
                    break
            if len(suggestions) >= limit:
                break
        if len(suggestions) >= limit:
            break

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "county": county,
        "suggestion_count": len(suggestions),
        "suggestions": suggestions,
        "note": "Advisory only — requires facility transfer approval; does not move stock",
        "developer": "BAHATI GAD WANGWE",
    }


def facility_supply_health(db: Session, *, facility_id: UUID) -> dict:
    rows = db.execute(
        select(InventoryItem, Medication)
        .join(Medication, Medication.id == InventoryItem.medication_id)
        .where(
            InventoryItem.facility_id == facility_id,
            InventoryItem.status == "ACTIVE",
            Medication.status == "ACTIVE",
        )
    ).all()
    counts = defaultdict(int)
    critical = []
    for inv, med in rows:
        risk = _risk_level(float(inv.current_quantity or 0), float(inv.minimum_quantity or 0))
        counts[risk] += 1
        if risk in {"STOCKOUT", "CRITICAL"}:
            critical.append(
                {
                    "medication_code": med.code,
                    "medication_name": med.name,
                    "current_quantity": float(inv.current_quantity or 0),
                    "minimum_quantity": float(inv.minimum_quantity or 0),
                    "risk": risk,
                }
            )
    return {
        "facility_id": str(facility_id),
        "sku_count": len(rows),
        "risk_counts": dict(counts),
        "critical_items": critical[:50],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
