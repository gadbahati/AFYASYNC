"""Claims integrity signals — duplicates, outliers, rapid resubmits.

Signals are investigative flags, not proof of fraud.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.claims.models import Claim
from app.encounters.models import Encounter


def _dec(v) -> float:
    if v is None:
        return 0.0
    return float(Decimal(str(v)))


def facility_integrity_scan(
    db: Session,
    *,
    facility_id: UUID,
    days: int = 30,
) -> dict:
    days = max(7, min(days, 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    rows = list(
        db.execute(
            select(Claim, Encounter)
            .join(Encounter, Encounter.id == Claim.encounter_id)
            .where(
                Encounter.facility_id == facility_id,
                Claim.updated_at >= since,
            )
            .order_by(Claim.updated_at.desc())
            .limit(2000)
        ).all()
    )

    signals: list[dict] = []
    by_patient_day: dict[tuple, list] = defaultdict(list)
    amounts: list[float] = []

    for claim, enc in rows:
        amt = _dec(claim.claim_amount)
        amounts.append(amt)
        day_key = (
            str(claim.patient_id),
            (claim.submitted_at or claim.updated_at).date().isoformat()
            if (claim.submitted_at or claim.updated_at)
            else "unknown",
        )
        by_patient_day[day_key].append(claim)

    # 1) Same patient, same day, multiple claims
    for (patient_id, day), claims in by_patient_day.items():
        if len(claims) >= 3:
            signals.append(
                {
                    "code": "MULTI_CLAIM_SAME_DAY",
                    "severity": "HIGH" if len(claims) >= 5 else "MEDIUM",
                    "patient_id": patient_id,
                    "day": day,
                    "claim_count": len(claims),
                    "claim_ids": [c.claim_id for c in claims[:10]],
                    "message": f"{len(claims)} claims for same patient on {day}",
                }
            )

    # 2) Amount outliers vs facility mean (simple z-style)
    if len(amounts) >= 5:
        mean = sum(amounts) / len(amounts)
        var = sum((a - mean) ** 2 for a in amounts) / len(amounts)
        std = var ** 0.5
        if std > 0:
            for claim, enc in rows:
                amt = _dec(claim.claim_amount)
                z = (amt - mean) / std
                if z >= 3.0 and amt > 0:
                    signals.append(
                        {
                            "code": "AMOUNT_OUTLIER",
                            "severity": "HIGH" if z >= 4 else "MEDIUM",
                            "claim_id": claim.claim_id,
                            "patient_id": str(claim.patient_id),
                            "claim_amount": amt,
                            "z_score": round(z, 2),
                            "message": f"Claim amount {amt} is {z:.1f} SD above facility mean",
                        }
                    )

    # 3) Rapid resubmit: DRAFT/REJECTED -> SUBMITTED churn same claim_id pattern
    status_counts: dict[str, int] = defaultdict(int)
    for claim, _ in rows:
        status_counts[str(claim.status)] += 1

    # 4) Zero or negative amounts (data integrity)
    for claim, _ in rows:
        amt = _dec(claim.claim_amount)
        if amt <= 0 and claim.status not in {"DRAFT", "CANCELLED"}:
            signals.append(
                {
                    "code": "NON_POSITIVE_AMOUNT",
                    "severity": "MEDIUM",
                    "claim_id": claim.claim_id,
                    "status": claim.status,
                    "claim_amount": amt,
                    "message": "Non-positive claim amount in non-draft status",
                }
            )

    # Cap signals for response size
    severity_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    signals.sort(key=lambda s: (severity_rank.get(s.get("severity", "LOW"), 9), s.get("code", "")))
    high = sum(1 for s in signals if s.get("severity") == "HIGH")
    medium = sum(1 for s in signals if s.get("severity") == "MEDIUM")

    integrity_score = 100.0
    integrity_score -= high * 8
    integrity_score -= medium * 3
    integrity_score = round(max(0.0, min(100.0, integrity_score)), 1)
    if integrity_score >= 80:
        band = "GREEN"
    elif integrity_score >= 60:
        band = "AMBER"
    else:
        band = "RED"

    return {
        "facility_id": str(facility_id),
        "window_days": days,
        "claims_scanned": len(rows),
        "status_counts": dict(status_counts),
        "signal_count": len(signals),
        "high_severity": high,
        "medium_severity": medium,
        "integrity_score": integrity_score,
        "band": band,
        "signals": signals[:100],
        "disclaimer": "Signals require human review — not automatic fraud findings",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def national_integrity_overview(db: Session, *, days: int = 30, limit: int = 30) -> dict:
    """Light national view: claim volume by status in window (no patient dump)."""
    days = max(7, min(days, 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    status_rows = db.execute(
        select(Claim.status, func.count())
        .where(Claim.updated_at >= since)
        .group_by(Claim.status)
    ).all()
    total = sum(int(c) for _, c in status_rows)
    by_status = {str(s): int(c) for s, c in status_rows}

    # Top facilities by claim volume via encounter join
    top = list(
        db.execute(
            select(Encounter.facility_id, func.count())
            .select_from(Claim)
            .join(Encounter, Encounter.id == Claim.encounter_id)
            .where(Claim.updated_at >= since)
            .group_by(Encounter.facility_id)
            .order_by(func.count().desc())
            .limit(limit)
        ).all()
    )

    return {
        "window_days": days,
        "claims_in_window": total,
        "by_status": by_status,
        "top_facilities_by_volume": [
            {"facility_id": str(fid), "claim_count": int(cnt)} for fid, cnt in top
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Use facility-scan for detailed integrity signals",
        "developer": "BAHATI GAD WANGWE",
    }
